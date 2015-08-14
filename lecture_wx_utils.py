import re
import lecture_utils

p1 = re.compile('^ME_*([0-9]+)_lecture_([0-9]+)_')

git_dir = '/Users/rkrauss/git/wxpython_guis/'

semester_root = '/Users/rkrauss/siue/classes/Fall_2015/'

course_roots = {'450':'/Users/rkrauss/Fall_2015_classes/450_Fall_2015/prep/', \
                '458':'/Users/rkrauss/Fall_2015_classes/458_Fall_2015/prep/', \
                }


lecture_roots = {'450':'/Users/rkrauss/Fall_2015_classes/450_Fall_2015/lectures/', \
                 '458':'/Users/rkrauss/Fall_2015_classes/458_Fall_2015/lectures/', \
                 }

course_class_dict = {'450':lecture_utils.course_450_tr, \
                     '458':lecture_utils.course_458}



