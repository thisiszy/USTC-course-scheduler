# USTC-course-scheduler

## Usage Example
```python
>>> from class_table import classTable
>>> mytable = classTable(student_id, password)
>>> mytable.login()
>>> mytable.course_code_list = ['CS1502','001549','011184','011705','MARX1004','018214','011094','011096','011103','011145','011175','017082']
>>> mytable.print_semester_id_map() # check semester and its id
>>> mytable.semester = "141" # set semester '2020年春季学期'
>>> mytable.update_db('141') # download lesson info for  '2020年春季学期'
>>> mytable.solve()
>>> mytable.print_class_table(0) #print lessons for week 1
```