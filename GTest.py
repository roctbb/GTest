import base64

import functools
import tornado.ioloop
import tornado.web
from pymongo import MongoClient
from bson.objectid import ObjectId
import markdown


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
            print(auth_decoded)
            username, password = auth_decoded.decode('ascii').split(':', 2)

            if (username == 'user1' and password == "pass1"):
                f(*args)
            else:
                _request_auth(handler)

        return new_f

    return decore


connection = MongoClient("mongodb://localhost:27017/quizer")
database = connection["quizer"]
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
                q["text"] = markdown.markdown(q["text"])
                questions[direction].append(q)

        print()
        print(questions)
        self.render("test.html", questions=questions)

    def post(self):
        user_id = self.get_cookie('user')
        print(user_id)
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
            print(question)
            print(id)
            if question["type"] == "var":
                for i in range(len(question["variants"])):
                    var = self.get_argument(id + "-" + str(i), '')
                    if var != '':
                        answers[id]["answer_variants"].append(i)
            else:
                answer = self.get_argument(id, "")
                if answer != "":
                    answers[id]["answer"] = answer
        student["answers"] = list(answers.values())
        student["submitted"] = True
        student["checked"] = False
        print(student)
        students_collection.update({'_id': ObjectId(user_id)}, student)

        self.redirect('/submit')


class SubmitHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("submit.html")


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
                q["text"] = markdown.markdown(q["text"])
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
        print(type)
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
            answers[answer["direction"]].append(answer)
        questions = list(question_collection.find())

        for direction in directions:
            summa = 0
            for answer in user['answers']:
                if answer["direction"] == direction:
                    summa += int(answer["points"])
            user[direction] = summa
        print(user)
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
        (r"/submit", SubmitHandler),
        (r"/admin", StudentsListHandler),
        (r"/admin/delete", QuestionDeleteHandler),
        (r"/admin/answers", StudentsAnswersHandler),
        (r'/images/(.*)', tornado.web.StaticFileHandler, {'path': 'images'}),
        (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static'})
    ], debug=True)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
