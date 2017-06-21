import tornado.ioloop
import tornado.web
from pymongo import MongoClient
from bson.objectid import ObjectId

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
                    if  var != '':
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

class StudentsAnswersHandler(tornado.web.RequestHandler):
    def get(self):
        id = self.get_argument("id")
        user = students_collection.find_one({"_id": ObjectId(id)})
        answers = {}
        directions = ['base', 'bio', 'robo', 'data', 'prog']
        for dir in directions:
            answers[dir] = []
        for answer in user["answers"]:
            print(user["answers"])
            answers[answer["direction"]].append(answer)
        questions = question_collection.find()
        self.render("answers.html", answers=answers, questions=questions)
        dict = {}
        for direction in directions:
            summa = 0
            for answer in user['answers']:
                if answer["type"]==direction:
                    sum+=answer["points"]
            user["direction"]=summa
            #self.write(direction, "-", summa, "\n")


    def post(self):
        id = self.get_argument("id")
        user = students_collection.find_one({"_id": ObjectId(id)})
        for answer in user["answers"]:
            points = self.get_argument(str(answer['_id']), 0)
            answer["points"]=points
        user["checked"] = True
        students_collection.update({'_id': ObjectId(id)}, user)
        self.redirect("/admin/answers?id="+id)



# class QuestionRegistrationHandler(tornado.web.RequestHandler):
#     def get(self):
#         self.render("question_registrate.html")
#     def post(self):
#         type = self.get_argument("type")
#         text = self.get_argument("text")
#         level = self.get_argument("level")




# class


class SubmitHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("submit.html")


def make_app():
    return tornado.web.Application([
        (r"/", StudentRegistrationHandler),
        (r"/test", StudentTestingHandler),
        (r"/submit", SubmitHandler),
        (r"/admin/answers", StudentsAnswersHandler)
    ], debug=True)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()


    # user_id = self.get_secure_cookie("user")
