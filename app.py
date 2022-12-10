from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

from pymongo import MongoClient

client = MongoClient('mongodb+srv://test:sparta@cluster0.ozvefus.mongodb.net/Clurster0?retryWrites=true&w=majority')
db = client.dbsparta


@app.route('/')
def home():
    return render_template('index.html')


@app.route("/bucket", methods=["GET"])
def bucket_get():
    #음식의 모든 정보를 html로 넘겨준다
    food_list = list(db.menu.find({}, {'_id': False}))
    #재료의 모든 정보를 html로 넘겨준다
    ingredient_list = list(db.ingredient.find({}, {'_id': False}))

    return jsonify({'menu': food_list, 'ingredient': ingredient_list})
   

@app.route("/bucket", methods=["POST"])
def bucket_post():
    food_receive = request.form['menu_give']
    day_receive = request.form['day_give']

    Menu = ['김치찌개', '동태찌개', '부대찌개', '청국장']
    Week = ['월', '화', '수', '목', '금', '토', '일']
    #입력된 음식이 메뉴에 없으면
    if food_receive not in Menu:
        return jsonify({'msg': '메뉴에 없는 음식입니다. 다시 입력하세요'})
    #입력된 요일이 잘못돼었으면
    if day_receive not in Week:
        return jsonify({'msg': '요일을 잘못 입력하셨습니다. 다시 입력하세요'})

    #db에서 클라이언트가 준 food_receive(음식)의 정보를 받아온다.
    menu_list = list(db.menu.find({'name': food_receive}, {'_id': False}))

    #만약 음식 정보가 없으면 (처음으로 음식을 입력할 경우)
    if len(menu_list) == 0:

        days = {'월': 0, '화': 0, '수': 0, '목': 0, '금': 0, '토': 0, '일': 0}

        #day_receive(요일)의 맞춰서 밸류값을 증가
        for day in days.keys():
            if day == day_receive:
                days[day] = days[day] + 1
                break

        doc = {
            'name': food_receive,
            'Day': days,
            'num': 1
        }

        db.menu.insert_one(doc)

    #이미 등록된 음식이라면
    else:
        food_ingredient = {'김치찌개': ['마늘', '양파', '대파', '소금'], '청국장': ['양파', '대파'],
                 '부대찌개': ['마늘', '소금'], '동태찌개': ['소금']}

        #food_receive(키값)에 맞는 밸류값들(재료들)을 하나씩 감소시킨다
        for ingredient in food_ingredient[food_receive]:
            find_ingre = list(db.ingredient.find({'name': ingredient}, {'_id': False}))
            new_num = int(find_ingre[0]['num']) - 1
            #감소된 재료를 db에 업데이트 한다
            db.ingredient.update_one({'name': ingredient}, {'$set': {'num': new_num}})

        ###음식판매 숫자 증가시키기###
        #food_receive(판매된 음식)의 정보를 받아온다
        food = list(db.menu.find({'name': food_receive}, {'_id': False}))
        #음식의 기존 판매량에 1을 더해줌
        new_num = int(food[0]['num']) + 1

        #44줄 dictionay값
        day_dic = food[0]['Day']

        #day_dic을 돌려 맞는 요일을 하나 증가시켜줌
        for day in day_dic.keys():
            if day == day_receive:
                day_dic[day] = day_dic[day] + 1
                break
        #음식의 판매량과 요일의 값을 업데이트
        db.menu.update_one({'name': food_receive}, {'$set': {'num': new_num}})
        db.menu.update_one({'name': food_receive}, {'$set': {'Day': day_dic}})

    return jsonify({'msg': '등록완료'})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)