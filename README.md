# USTC-course-scheduler

## Prerequisite
### Linux
```bash
sudo apt-get update
sudo apt-get install libleptonica-dev 
sudo apt-get install tesseract-ocr
sudo apt-get install libtesseract-dev

cd USTC-course-scheduler
pip install -r requirements.txt
```
### Windows
#### Step 1
install tesseract see:
https://stackoverflow.com/questions/50951955/pytesseract-tesseractnotfound-error-tesseract-is-not-installed-or-its-not-i
#### Step 2
```bash
cd USTC-course-scheduler
pip install -r requirements.txt
```
### MacOS
```bash
brew install tesseract

cd USTC-course-scheduler
pip install -r requirements.txt
```

## Usage Example
### Method 1 (Recommend)
```bash
python3 class_table.py
```

### Method 2
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