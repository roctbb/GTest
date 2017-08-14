import base64
import os
import functools
import uuid

import tornado.ioloop
import tornado.web
from pymongo import MongoClient
from bson.objectid import ObjectId
import markdown2

def html_to_text(html):
    import re, cgi
    tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')

    # Remove well-formed tags, fixing mistakes by legitimate users
    no_tags = tag_re.sub('', html)

    # Clean up anything else by escaping
    ready_for_web = cgi.escape(no_tags)
    return ready_for_web

def authenticated():
    def decore(f):
        def _request_auth(handler):
            handler.set_header('WWW-Authenticate', 'Basic realm=tmr')
            handler.set_status(401)
            handler.finish()
            return False

        @functools.wraps(f)
        def new_f(*args):
            handler = args[0]

            auth_header = handler.request.headers.get('Authorization')
            if auth_header is None:
                return _request_auth(handler)
            if not auth_header.startswith('Basic '):
                return _request_auth(handler)

            auth_decoded = base64.decodestring(auth_header[6:].encode('ascii'))
            username, password = auth_decoded.decode('ascii').split(':', 2)

            if (username == 'GoTo' and password == "GoTo"):
                f(*args)
            else:
                _request_auth(handler)

        return new_f

    return decore


#connection = MongoClient("mongodb://localhost:27017/quizer")
connection = MongoClient("mongodb://GoTo:GoTo@ds143532.mlab.com:43532/gtest")
database = connection["gtest"]
#database = connection["quizer"]
students_collection = database["Students"]
question_collection = database["Questions"]


class StudentRegistrationHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("registration.html")

    def post(self):
        name = self.get_argument("name")
        student = {"name": name, "submitted": False}
        students_collection.insert_one(student)
        user_id = self.set_cookie("user", str(student['_id']))
        return self.redirect('/test')


class StudentTestingHandler(tornado.web.RequestHandler):
    def get(self):
        questions = {}
        directions = ["robo", "prog", "data", "bio", "base"]
        for direction in directions:
            questions[direction] = []
            temp = list(question_collection.find({"direction": direction}))
            for q in temp:
                q["text"] = markdown2.markdown(q["text"], extras=["fenced-code-blocks", "break-on-newline", "tables"])
                questions[direction].append(q)
        self.render("test.html", questions=questions)

    def post(self):
        user_id = self.get_cookie('user')
        student = students_collection.find_one({"_id": ObjectId(user_id)})
        questions = list(question_collection.find())
        answers = {}
        for question in questions:
            id = str(question["_id"])
            answers[id] = question
            answers[id]["answer"] = ""
            answers[id]["answer_variants"] = []
            answers[id]["points"] = 0

        for question in questions:
            id = str(question["_id"])
            if question["type"] == "var":
                for i in range(len(question["variants"])):
                    var = self.get_argument(id + "-" + str(i), '')
                    if var != '':
                        answers[id]["answer_variants"].append(i)
            else:
                answer = self.get_argument(id, "")
                if answer != "":
                    answers[id]["answer"] = html_to_text(answer)
        student["answers"] = list(answers.values())
        student["submitted"] = True
        student["checked"] = False
        students_collection.update({'_id': ObjectId(user_id)}, student)

        self.redirect('/submit')


class SubmitHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("submit.html")


class UploadHandler(tornado.web.RequestHandler):
    @authenticated()
    def get(self):
        self.render("uploader.html", result="")

    @authenticated()
    def post(self):
        fileinfo = self.request.files['image'][0]
        fname = fileinfo['filename']
        extn = os.path.splitext(fname)[1]
        cname = str(uuid.uuid4()) + extn
        path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images/' + cname);
        fh = open(path, 'wb')
        fh.write(fileinfo['body'])

        self.render("uploader.html", result='images/' + cname)


class StudentsListHandler(tornado.web.RequestHandler):
    @authenticated()
    def get(self):
        selected_tab = self.get_argument("direction", 'table')
        students = students_collection.find({"submitted": True})
        questions = {}
        directions = ["robo", "prog", "data", "bio", "base"]
        
        for direction in directions:
            questions[direction] = []
            temp = list(question_collection.find({"direction": direction}))
            for q in temp:
                q["text"] = markdown2.markdown(q["text"], extras=["fenced-code-blocks", "break-on-newline", "tables"])
                questions[direction].append(q)
        self.render("table.html", students=students, questions=questions, selected_tab=selected_tab)

    @authenticated()
    def post(self):
        type = self.get_argument("type")

        if type == "txt":
            text = self.get_argument("text")
            level = "start"
            direction = self.get_argument("direction")
            question = {"text": text,
                        "direction": direction,
                        "type": type,
                        "level": level
                        }
            question_collection.insert_one(question)

        elif type == "var":
            text = self.get_argument("text")
            level = "start"
            direction = self.get_argument("direction")
            variants = []
            for i in range(0, 4):
                variants.append(self.get_argument("variants" + str(i)))
            question = {"text": text,
                        "variants": variants,
                        "direction": direction,
                        "type": type,
                        "level": level
                        }
            question_collection.insert_one(question)
        self.redirect('/admin?direction='+direction)

class QuestionDeleteHandler(tornado.web.RequestHandler):
    @authenticated()
    def get(self):
        id = self.get_argument("id")
        question = question_collection.find_one({'_id': ObjectId(id)})
        question_collection.delete_one({'_id': ObjectId(id)})
        self.redirect('/admin?direction=' + question['direction'])

class StudentsAnswersHandler(tornado.web.RequestHandler):
    @authenticated()
    def get(self):
        id = self.get_argument("id")
        user = students_collection.find_one({"_id": ObjectId(id)})
        answers = {}
        directions = ['base', 'bio', 'robo', 'data', 'prog']
        for dir in directions:
            answers[dir] = []
        for answer in user["answers"]:
            answer["text"] = markdown2.markdown(answer["text"], extras=["fenced-code-blocks", "break-on-newline", "tables"])
            if answer["type"] == "txt":
                answer["answer"] = markdown2.markdown(answer["answer"], extras=["fenced-code-blocks", "break-on-newline", "tables"])
            answers[answer["direction"]].append(answer)
        questions = list(question_collection.find())

        for direction in directions:
            summa = 0
            for answer in user['answers']:
                if answer["direction"] == direction:
                    try:
		        summa += float(str(answer["points"]).replace(',', '.'))
                    except:
                        ### Wrong number of points set
                        pass
            user[direction] = summa
        self.render("answers.html", answers=answers, questions=questions, user=user)

    @authenticated()
    def post(self):
        id = self.get_argument("id")
        user = students_collection.find_one({"_id": ObjectId(id)})
        for answer in user["answers"]:
            points = self.get_argument(str(answer['_id']), 0)
            answer["points"] = points
        user["checked"] = True

        students_collection.update({'_id': ObjectId(id)}, user)
        self.redirect("/admin/answers?id=" + id)


def make_app():
    return tornado.web.Application([
        (r"/", StudentRegistrationHandler),
        (r"/test", StudentTestingHandler),
        (r"/upload", UploadHandler),
        (r"/submit", SubmitHandler),
        (r"/admin", StudentsListHandler),
        (r"/admin/delete", QuestionDeleteHandler),
        (r"/admin/answers", StudentsAnswersHandler),
        (r'/images/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(os.path.realpath(__file__)),'images')}),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(os.path.realpath(__file__)),'static')})
    ], debug=True)


if __name__ == "__main__":
    app = make_app()
    app.listen(2017)
    tornado.ioloop.IOLoop.current().start()
