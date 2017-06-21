import tornado.ioloop
import tornado.web
from bson.objectid import ObjectId
from pymongo import MongoClient

connection = MongoClient("mongodb://Danya:lopata@ds129352.mlab.com:29352/gth_tests")
database = connection["gth_tests"]
students_collection = database["Students"]
question_collection = database["Questions"]


class StudentRegistrationHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("registration.html")

    def post(self):
        name = self.get_argument("name")
        student = {"name": name, "submitted": False}
        students_collection.insert_one(student)
        print(student['_id'])
        user_id = self.set_cookie("user", str(student['_id']))
        return self.redirect('/test')


class StudentTestingHandler(tornado.web.RequestHandler):
    def get(self):
        questions = {}
        directions = ["robo", "prog", "data", "bio", "base"]
        for direction in directions:
            questions[direction] = list(question_collection.find({"direction": direction}))
        users=list(question_collection.find({"submitted":True}))
        self.render("test.html", questions=questions, users=users)

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
                    if  var != '':
                        answers[id]["answer_variants"].append(i)
            else:
                answer = self.get_argument(id, "")
                if answer != "":
                    answers[id]["answer"] = answer
        student["answers"] = answers
        student["submitted"] = True
        print(student)
        students_collection.update({'_id': ObjectId(user_id)}, student)

        self.redirect('/submit')


class QuestionRegistrationHandler(tornado.web.RequestHandler):
    def get(self):
        questions = {}
        directions = ["robo", "prog", "data", "bio", "base"]
        for direction in directions:
            questions[direction] = list(question_collection.find({"direction": direction}))
        print()
        print(questions)
        self.render("question_registrate.html")
        # type = self.get_argument("type")

    def post(self):
        type = self.get_argument("type")

        if type=="txt":
            text = self.get_argument("text")
            level = self.get_argument("level")
            direction = self.get_argument("direction")
            question = {"text": text,
                        "direction": direction,
                        "type": type,
                        "level": level
                        }
            question_collection.insert_one(question)

        elif type=="var":
            text = self.get_argument("text")
            level = self.get_argument("level")
            direction = self.get_argument("direction")
            variants = []
            for i in range(0, 4):
                variants.append(self.get_argument("variants"))
            question = {"text": text,
                        "variants": variants,
                        "direction": direction,
                        "type": type,
                        "level": level
                        }
            question_collection.insert_one(question)


# class


class SubmitHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("submit.html")


def make_app():
    return tornado.web.Application([
        (r"/", StudentRegistrationHandler),
        (r"/test", StudentTestingHandler)
    ], debug=True)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()






    # user_id = self.get_secure_cookie("user")
