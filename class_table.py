import io
import os
import PIL
import pytesseract
import re
import requests
from bs4 import BeautifulSoup
from typing import *
import json
import sqlite3
from tqdm import tqdm
import z3
from prettytable import PrettyTable
import pickle


'''
>>> from class_table import classTable
>>> mytable = classTable("PB12345678", "qwert123")
>>> mytable.course_code_list = ['CS1502','001549','011184','011705','MARX1004','018214','011094','011096','011103','011145','011175','017082']
>>> mytable.semester = "141"
>>> mytable.solve()
'''

class Alarm:
    OK = '\033[92m' #GREEN
    WARNING = '\033[93m' #YELLOW
    FAIL = '\033[91m' #RED
    RESET = '\033[0m' #RESET COLOR
    
    def success(msg: str) -> None:
        print(Alarm.OK + "[SUCC] " + Alarm.RESET + msg)
    
    def warning(msg: str) -> None:
        print(Alarm.WARNING + "[WARN] " + Alarm.RESET + msg)

    def fail(msg: str) -> None:
        print(Alarm.FAIL + "[FAIL] " + Alarm.RESET + msg)
    
    def info(msg: str) -> None:
        print("[INFO] " + msg)

class classTable:
    __username = ""
    __password = ""
    __session = None
    # class table for one semester
    __place_table = []
    __history_model = []
    # the semester you need to schedule class table
    semester = ''
    # courses code list you want to schedule
    course_code_list = []
    __prefer_class_list = []

    def __init__(self, usrname, pwd) -> None:
        '''
        return the classTable object, will NOT login your account automatically
        >>> myTable = classTable("PB12345678", "qwert123")
        If you want to login, use login()
        >>> mytable.login()
        '''
        self.__username = usrname
        self.__password = pwd

    def _check_login(self):
        if self.__session is None:
            Alarm.fail("Please use login() first!")
            raise Exception("Please use login() first!")

    def clear(self):
        '''
        clear all history_model, __prefer_class_list
        each time you call solve(), the class table solved will be saved to history_model
        '''
        self.__history_model = []
        self.__prefer_class_list = []
        Alarm.success("History model and Prefer class cleared")
    
    def save_history_model(self):
        with open('history.plk', 'wb') as f:
            pickle.dump(self.__history_model, f, pickle.HIGHEST_PROTOCOL)
    
    def load_history_model(self):
        with open('history.plk', 'rb') as f:
            self.__history_model = pickle.load(f)

    def config(self):
        '''
        set semester and course code
        course code is the only identifier of a course, for example the code for "计算机网络" is "011144"
        '''
        self._check_login()
        self.print_semester_id_map()
        print("Please input the semester you want to schedule class table:")
        self.semester = input()
        print("Please input class codes, end with 0000")
        code = input()
        while code != '0000':
            self.course_code_list.append(code)
            code = input()
        Alarm.success("Config done!")

    def login(self) -> None:
        '''
        login your account
        login logic from https://github.com/iBug/thu-checkin
        '''
        # https://stackoverflow.com/a/35504626/5958455
        from urllib3.util.retry import Retry
        from requests.adapters import HTTPAdapter

        CAS_LOGIN_URL = "https://passport.ustc.edu.cn/login"
        CAS_CAPTCHA_URL = "https://passport.ustc.edu.cn/validatecode.jsp?type=login"
        CAS_RETURN_URL = "https://jw.ustc.edu.cn/ucas-sso/login"

        retries = Retry(total=2,
                        backoff_factor=0.5,
                        status_forcelist=[500, 502, 503, 504])

        self.__session = requests.Session()
        self.__session.mount("https://", HTTPAdapter(max_retries=retries))
        self.__session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36 Edg/92.0.902.67"
        r = self.__session.get(CAS_LOGIN_URL, params={"service": CAS_RETURN_URL})
        x = re.search(r"""<input.*?name="CAS_LT".*?>""", r.text).group(0)
        cas_lt = re.search(r'value="(LT-\w*)"', x).group(1)

        r = self.__session.get(CAS_CAPTCHA_URL)
        img = PIL.Image.open(io.BytesIO(r.content))
        pix = img.load()
        for i in range(img.size[0]):
            for j in range(img.size[1]):
                r, g, b = pix[i, j]
                if g >= 40 and r < 80:
                    pix[i, j] = (0, 0, 0)
                else:
                    pix[i, j] = (255, 255, 255)
        lt_code = pytesseract.image_to_string(img).strip()
        Alarm.success("Captcha done!")

        data = {
            "model": "uplogin.jsp",
            "service": CAS_RETURN_URL,
            "warn": "",
            "showCode": "1",
            "username": self.__username,
            "password": self.__password,
            "button": "",
            "CAS_LT": cas_lt,
            "LT": lt_code,
        }
        Alarm.info("Try login...")
        r = self.__session.post(CAS_LOGIN_URL, data=data)
        Alarm.success("Login Success!")

    def print_semester_id_map(self):
        '''
        print semester-id map
        I don't know why, the semester and id will map like this, it's full of confusion
        >>> mytable.print_semester_id_map()
        +----------------+-----+
        |    semester    |  id |
        +----------------+-----+
        | 2022年春季学期 | 241 |
        | 2021年秋季学期 | 221 |
        | 2021年夏季学期 | 202 |
        ...
        | 2000年秋季学期 |  13 |
        +----------------+-----+
        >>> mytable.semester = "202"    # if you want to schedule class table for 2021-Summer
        '''
        self._check_login()
        Alarm.info("Try get semester info...")
        r = self.__session.get("https://jw.ustc.edu.cn/for-std/lesson-search/index/24441")
        if r.status_code != 200:
            Alarm.fail("Semester info get failed")
            raise Exception("Semester info get failed")
        else:
            soup = BeautifulSoup(r.text, "html.parser")
            semester = soup.find("select", {"id": "semester"})
            semester_id_table = {item.attrs['value']: item.text for item in semester.find_all("option")}
            Alarm.success("Get semester info success")
        table = PrettyTable(['semester', 'id'])
        for key, value in semester_id_table.items():
            table.add_row([value, key])
        print(table)

    def _get_courses_by_semester(self, semester_id: str) -> List[Dict[str, str]]:
        if semester_id == None or semester_id == "":
            Alarm.fail("Semester id is empty")
            raise Exception("Semester id is empty")
        r = self.__session.get("https://jw.ustc.edu.cn/for-std/lesson-search/semester/%s/search/24441?queryPage__=1%%2C1&sort__=code%%2Casc" % (semester_id))
        if r.status_code != 200:
            print("Courses get failed")
            raise Exception("Courses get failed")
        course_cnt = json.loads(r.text)['_page_']['totalRows']
        Alarm.info("Course cnt: %d" % (course_cnt))
        course_info_list = []
        page_cnt = 1
        max_retry = 3
        while(course_cnt - (page_cnt - 1) * 1000> 0):
            Alarm.info("Try get courses page %d" % (page_cnt))
            r = self.__session.get("https://jw.ustc.edu.cn/for-std/lesson-search/semester/%s/search/24441?queryPage__=%s%%2C1000&sort__=code%%2Casc" % (semester_id, str(page_cnt)))
            if r.status_code != 200:
                Alarm.fail("Courses get failed")
                raise Exception("Courses get failed")
            else:
                try:
                    course_info_list += json.loads(r.text)['data']
                except:
                    max_retry -= 1
                    if max_retry == 0:
                        Alarm.fail("Courses get failed")
                        raise Exception("Courses get failed")
                    else:
                        Alarm.info("Page %d failed, retrying..." % (page_cnt))
                        continue
            page_cnt += 1
        Alarm.success("Get courses success, get %d courses" % (len(course_info_list)))
        return course_info_list

    def drop_database(self):
        '''
        drop class info database
        the database save in the same folder as this file with name "course.db"
        '''
        if os.path.exists("course.db"):
            Alarm.warning("Database exists, pls type 'Yes, Sure' to drop it")
            safe_word = input()
            if(safe_word != "Yes, Sure"):
                Alarm.success("Drop database cancelled")
                return
            con = sqlite3.connect('course.db')
            cur = con.cursor()
            try:
                cur.execute('''DELETE FROM courses''')
                Alarm.success("Database drop success")
            finally:
                con.commit()
                con.close()

    def _prepare_database(self):
        '''
        make sure the database exists, if not then create it
        '''
        Alarm.info("Prepare database...")
        if not os.path.exists("course.db"):
            con = sqlite3.connect('course.db')
            cur = con.cursor()
            # Create table
            cur.execute('''CREATE TABLE courses
                        (id integer, 
                        classCode text, 
                        courseCode text, 
                        courseName text, 
                        credits real, 
                        suggestScheduleWeeks text, 
                        semester integer, 
                        teacher text, 
                        timeTotal real,
                        timeTheory real,
                        timeExperiment real,
                        curNum integer,
                        maxNum integer,
                        scheduleWeek text,
                        scheduleTime text)''')
            con.commit()
            con.close()
            Alarm.success("Database created")

    def update_db(self, semester_id: str):
        '''
        add all course info in the new semester to the database
        '''
        self._check_login()
        if self.__session is None:
            Alarm.fail("Please use login() first!")
            return
        self._prepare_database()
        courses_info_list = self._get_courses_by_semester(semester_id)
        con = sqlite3.connect('course.db')
        cur = con.cursor()
        try:
            for item in tqdm(courses_info_list):
                if item['teacherAssignmentList'] != []:
                    teacher = item['teacherAssignmentList'][0]['teacher']['person']['nameZh']
                else:
                    teacher = None
                cur.execute("INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                        item['id'], 
                        item['code'], 
                        item['course']['code'], 
                        item['course']['nameZh'], 
                        item['course']['credits'], 
                        json.dumps(item['suggestScheduleWeeks']), 
                        item['semester']['id'], 
                        teacher, 
                        item['requiredPeriodInfo']['total'], 
                        item['requiredPeriodInfo']['theory'], 
                        item['requiredPeriodInfo']['practice'],
                        item['stdCount'],
                        item['limitCount'],
                        item['scheduleText']['dateTimeText']['text'],
                        item['scheduleText']['dateTimePlaceText']['text'],
                    )
                )
        except Exception as e:
            Alarm.warning("some error occured, pls check")
            print(item, e)
        finally:
            con.commit()
            con.close()
        Alarm.success("Database updated")

    def _get_courses_info(self) -> Dict[str, list]:
        Alarm.info("Extracting schedule...")
        con = sqlite3.connect('course.db')
        cur = con.cursor()
        course_list = {}
        for courseCode in tqdm(self.course_code_list):
            try:
                result = cur.execute("SELECT scheduleWeek, scheduleTime, courseName, classCode FROM courses WHERE courseCode = '%s' AND semester = '%s'" % (courseCode, self.semester)).fetchall()
                course_list[courseCode] = result
            except sqlite3.OperationalError as e:
                Alarm.fail("Error with course code: %s" % (courseCode))
                continue
        con.close()
        Alarm.success("Schedule extracted")
        return course_list

    def _extract_schedule(self, course: Tuple[str]):
        if len(course[0].split(';')) != len(course[1].split(';')):
            places_raw = zip(course[0].split(';') * len(course[1].split(';')), course[1].split(';'))
        else:
            places_raw = zip(course[0].split(';'), course[1].split(';'))
        schedule = []
        for weeks_raw, places in places_raw:
            week_list = []
            # split ','
            t = weeks_raw.split(',')
            for week_string in t:
                week = re.findall(r'\d+', week_string)
                if len(week) == 1:
                    week_list += [int(week[0])]
                elif len(week) == 2:
                    if re.findall(r'单', week_string):
                        week_list += [item for item in list(range(int(week[0]), int(week[1]) + 1)) if item % 2 == 1]
                    elif re.findall(r'双', week_string):
                        week_list += [item for item in list(range(int(week[0]), int(week[1]) + 1)) if item % 2 == 0]
                    else:
                        week_list += list(range(int(week[0]), int(week[1]) + 1))
                else:
                    print(week)
                    raise Exception("week error")

            room, day_time = places.split(':')
            # print(room)
            day = int(re.findall(r'\d+', day_time)[0])
            day_lessons = re.findall(r'\d+', re.findall(r'\(.*\)', day_time)[0])
            places_list = [(day, int(item)) for item in day_lessons]
            schedule.append((week_list, places_list))
            
        return schedule, course[2], course[3]

    def _add_constraint(self, course_list: Dict[str, list]) -> z3.And():
        Alarm.info("Adding constraint...")
        if course_list == []:
            Alarm.fail("No course")
            return z3.And()
        class_map = {}
        # class code var
        ClassVar = {}
        cnt = 0
        # class place var
        __place_table = [[[[] for time in range(1, 14)] for week in range(1, 8)] for week in range(1, 19)]
        for courseCode in self.course_code_list:
            class_map[courseCode] = {}
            for course in course_list[courseCode]:
                class_map[courseCode][cnt] = self._extract_schedule(course)
                ClassVar[cnt] = z3.Bool('%s_%i' % (class_map[courseCode][cnt][2], cnt))
                schedule_list , _, _ = class_map[courseCode][cnt]
                for weeks, days in schedule_list:
                    for week in weeks:
                        for day, time in days:
                            try:
                                __place_table[week-1][day-1][time-1].append(ClassVar[cnt])
                            except Exception as e:
                                print(week, day, time)
                cnt += 1

        place_constraint_list = []
        for week in __place_table:
            for day in week:
                for time in day:
                    one_place_constraint_list = []
                    if len(time) > 1:
                        for lesson in time:
                            one_place_constraint_list.append(z3.And(lesson, z3.And([z3.Not(k) for k in time if k.get_id() != lesson.get_id()])))
                        place_constraint_list.append(z3.Or(z3.Or(one_place_constraint_list), z3.And([z3.Not(k) for k in time])))
        place_constraint = z3.And(place_constraint_list)
        Alarm.info("Place constraint added")

        history_constraint_list = []
        for history in self.__history_model:
            one_history_constraint_list = []
            for item in history:
                for num in ClassVar:
                    if item == str(ClassVar[num]).split('_')[0]:
                        one_history_constraint_list.append(ClassVar[num])
            history_constraint_list.append(z3.Not(z3.And(one_history_constraint_list)))
        history_constraint = z3.And(history_constraint_list)
        Alarm.info("History constraint added")

        lesson_constraint_list = []
        for courseCode, cur_classes in class_map.items():
            one_class_constraint_list = []
            for class_id, class_schedule in cur_classes.items():
                # choose one class must not choose other same class
                one_class_constraint_list.append(z3.And(ClassVar[class_id], z3.And([z3.Not(ClassVar[k]) for k, _ in cur_classes.items() if k != class_id])))
            lesson_constraint_list.append(z3.Or(one_class_constraint_list))
        # same lesson only choose one class
        lesson_constraint = z3.And(lesson_constraint_list)
        Alarm.info("Course constraint added")

        prefer_constraint_list = []
        not_prefer_constraint_list = []
        for classTuple in self.__prefer_class_list:
            for prefer in classTuple[0]:
                for num in ClassVar:
                    if prefer == str(ClassVar[num]).split('_')[0]:
                        prefer_constraint_list.append(ClassVar[num])
            for not_prefer in classTuple[1]:
                for num in ClassVar:
                    if not_prefer == str(ClassVar[num]).split('_')[0]:
                        not_prefer_constraint_list.append(ClassVar[num])
        if len(self.__prefer_class_list) != 0:
            prefer_constraint = z3.And(z3.Or(prefer_constraint_list), z3.Not(z3.Or(not_prefer_constraint_list)))
        else:
            prefer_constraint = z3.And()
        Alarm.info("Prefer constraint added")
        Alarm.success("Constraint added")

        return z3.And(place_constraint, lesson_constraint, history_constraint, prefer_constraint)

    def _place_lessons(self, cur_classes: list):
        Alarm.info("Try to place lessons...")
        self.__place_table = [[[[] for _ in range(13)] for _ in range(7)] for _ in range(18)]
        con = sqlite3.connect('course.db')
        cur = con.cursor()
        for class_id in cur_classes:
            try:
                result = cur.execute("SELECT scheduleWeek, scheduleTime, courseName, classCode, courseName, teacher FROM courses WHERE classCode = '%s' AND semester = '%s'" % (class_id, self.semester)).fetchall()[0]
            except sqlite3.OperationalError as e:
                Alarm.fail("Error with class code: %s" % (class_id))
                continue

            schedule_list , _, _ = self._extract_schedule(result)
            for weeks, days in schedule_list:
                for week in weeks:
                    for day, time in days:
                        try:
                            assert self.__place_table[week-1][day-1][time-1] == []
                            self.__place_table[week-1][day-1][time-1] = (result[3], result[4], result[5])
                        except Exception as e:
                            Alarm.warning("Error with class code: %s" % (class_id))
                            print(week, day, time)
        con.close()
        Alarm.success("Schedule placed")

    def solve(self):
        '''
        get your class schedule solution and the solution will be saved to history_model
        if you want to clear history_model, use clear()
        if NO solution, will alarm "Not sat!"
        >>> myTable.solve() # get a class table schedule solution
        >>> myTable.solve() # get a new class table schedule solution different from the solution before
        >>> myTable.clear() # clear history_model
        '''
        Alarm.info("Solving...")
        sol = z3.Solver()
        sol.add(self._add_constraint(self._get_courses_info()))
        r = sol.check()
        if r != z3.sat:
            Alarm.fail("Not sat!")
            return
        model = sol.model()
        Alarm.success("Solved! Saving current solution")
        cur_classes = []
        for item in model:
            if model[item] == z3.BoolVal(True):
                cur_classes.append(str(item).split('_')[0])
        self.__history_model.append(cur_classes)
        Alarm.success("Solution saved, solution is " + str(cur_classes))
        self._place_lessons(cur_classes)

    def print_class_table(self, week):
        '''
        print class table at a specific week
        >>> myTable.print_class_table(0)    # print class table at week 1
        '''
        if self.__place_table == []:
            Alarm.warning("No place table, try to solve")
            self.solve()
        if week < 0 or week > 17:
            Alarm.fail("Invalid week")
            return
        table = PrettyTable(['Mon.','Tue.','Wed.','Thu.','Fri.','Sat.','Sun.'])
        table.add_rows([['\n'.join(self.__place_table[week][i][j])  if self.__place_table[week][i][j] != [] else '' for i in range(7)] for j in range(13)])
        print(table)

    def get_study_plan(self):
        self._check_login()
        if self.__session is None:
            Alarm.fail("Please use login() first!")
            return
        Alarm.info("Trying to get your plan...")
        r = self.__session.get("https://jw.ustc.edu.cn/for-std/program")
        soup = BeautifulSoup(r.text, "html.parser")
        plan = soup.find("a")
        Alarm.info("Your plan is: " + plan.text.strip("\n\t"))
        planurl = "https://jw.ustc.edu.cn/for-std/program/root-module-json/" + plan["href"].split('/')[-1]
        r = self.__session.get(planurl)
        lessons = json.loads(r.text)

        lessons['allPlanCourses'][0]
        lesson_list = {}
        for item in lessons['allPlanCourses']:
            if item['termTextZhs'][0] not in lesson_list:
                lesson_list[item['termTextZhs'][0]] = [(item['course']['nameZh'], item['course']['code'])]
            else:
                lesson_list[item['termTextZhs'][0]].append((item['course']['nameZh'], item['course']['code']))

        for k, v in lesson_list.items():
            print("--------------" + k + "--------------")
            for i in v:
                print(i[0] + " " + i[1])
    
    def _select_prefer_class(self):
        con = sqlite3.connect('course.db')
        cur = con.cursor()
        for courseCode in self.course_code_list:
            try:
                result = cur.execute("SELECT teacher, scheduleWeek, scheduleTime, courseName, classCode FROM courses WHERE courseCode = '%s' AND semester = '%s'" % (courseCode, self.semester)).fetchall()
                if len(result) == 0:
                    Alarm.fail("No such course: %s" % (courseCode))
                    return
                print("select your prefer class (seperate each class by ',' and skip select by press ENTER")
                print("--------------" + result[0][3] + "--------------")
                classes = []
                for item in result:
                    classes.append(item[4])
                    print("%s\t%s\t%s\t%s\t" % (item[0], item[1], item[2], item[4]))
                selects = input().split(',')
                if selects != ['']:
                    select_list = []
                    try:
                        for item in selects:
                            print(item.strip())
                            select_list.append(item.strip())
                            classes.remove(item.strip())
                        self.__prefer_class_list.append((select_list, classes))
                    except Exception as e:
                        Alarm.fail("Invalid input")
            except sqlite3.OperationalError as e:
                Alarm.fail("Error with course code: %s" % (courseCode))
        con.close()

if __name__ == "__main__":
    '''
    interactive mode
    '''
    print("Welcome to use class table generator!")
    print("Please use function sequentially!")
    table = PrettyTable(['Func Num', 'Func Name', 'Description'])
    # table.add_row(['0', 'help', 'print this table'])
    table.add_row(['1', 'login', 'login to your account'])
    table.add_row(['2', 'set semester', 'select your semester'])
    table.add_row(['3', 'set lessons', 'select your current semester lessons'])
    table.add_row(['4', 'update database', 'update course database from jw.ustc.edu.cn'])
    table.add_row(['5', 'add prefer class', 'select the class that you prefer'])
    table.add_row(['6', 'solve', 'get your class table solution'])
    table.add_row(['7', 'print class table', 'print your class table at a specific week'])
    table.add_row(['other', 'exit', 'exit the program'])
    print(table)
    while True:
        num = int(input())
        # if num == 0:
        #     print(table)
        if num == 1:
            print("Please input your username")
            username = input()
            print("Please input your password")
            password = input()
            myTable = classTable(username, password)
            myTable.login()
        elif num == 2:
            myTable.print_semester_id_map()
            print("Please input your semester id")
            semester_id = input()
            myTable.semester = semester_id.strip()
        elif num == 3:
            print("Here's your lessons, please input lessons you want to take, you only need to input lesson code(seperate each lesson by ',', e.g. \nCS1502.01, 011103.02, MARX1004.20 ")
            myTable.get_study_plan()
            lessons = input()
            myTable.course_code_list = []
            for item in lessons.split(','):
                myTable.course_code_list.append(item.strip())
        elif num == 4:
            print("Updating database, if it's the first time, please wait for a while, 'course.db' will be created")
            myTable.update_db(myTable.semester)
        elif num == 5:
            myTable._select_prefer_class()
        elif num == 6:
            myTable.solve()
        elif num == 7:
            print("Please input the week you want to print")
            week = input()
            myTable.print_class_table(int(week))
        else:
            break
        print(table)
