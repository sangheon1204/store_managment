from flask import Flask, render_template, jsonify, request, session, redirect, url_for

app = Flask(__name__)

from pymongo import MongoClient
import certifi

ca=certifi.where()

client = MongoClient("mongodb+srv://test:sparta@cluster0.cajtwuw.mongodb.net/?retryWrites=true&w=majority", tlsCAFile=ca)
db = client.dbsparta_plus_week4

# JWT 토큰을 만들 때 필요한 비밀문자열입니다. 아무거나 입력해도 괜찮습니다.
# 이 문자열은 서버만 알고있기 때문에, 내 서버에서만 토큰을 인코딩(=만들기)/디코딩(=풀기) 할 수 있습니다.
SECRET_KEY = 'STORE_MANAGE'

# JWT 패키지를 사용합니다. (설치해야할 패키지 이름: PyJWT)
import jwt

# 토큰에 만료시간을 줘야하기 때문에, datetime 모듈도 사용합니다.
import datetime

# 회원가입 시엔, 비밀번호를 암호화하여 DB에 저장해두는 게 좋습니다.
# 그렇지 않으면, 개발자(=나)가 회원들의 비밀번호를 볼 수 있으니까요.^^;
import hashlib

#re.함수를 사용하기 위해 추가하였습니다.
import re

#json 내장 모듈을 사용하기 위함
import json


#################################
##  HTML을 주는 부분             ##
#################################
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})
        return render_template('index.html', nickname=user_info["nick"])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

@app.route('/review')
def review():
    return render_template('review.html')

#################################
##  로그인을 위한 API            ##
#################################

# [회원가입 API]
# id, pw, nickname을 받아서, mongoDB에 저장합니다.
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route('/api/register', methods=['POST'])
def api_register():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    nickname_receive = request.form['nickname_give']
    userstore_receive = request.form['userstore_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    db.user.insert_one(
        {'id': id_receive, 'pw': pw_hash, 'nick': nickname_receive, 'userstore': userstore_receive})
    return jsonify({'result': 'success'})

#################################
##  ID, 닉네임 중복학인           ##
#################################

@app.route("/register/check_id", methods=["POST"])
def check_id():
    id_receive = request.form['id_give']
    user = db.user.find_one({'id': id_receive})
    if( user == None):
        return jsonify({'msg' : '1'})
    else:
        return jsonify({'msg' : '2'})


@app.route("/register/check_nick", methods=["POST"])
def check_nick():
    nick_receive = request.form['nick_give']
    user = db.user.find_one({'nick': nick_receive})
    if( user == None):
        return jsonify({'msg' : '1'})
    else:
        return jsonify({'msg' : '2'})



# [로그인 API]
# id, pw를 받아서 맞춰보고, 토큰을 만들어 발급합니다.
@app.route('/api/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.user.find_one({'id': id_receive, 'pw': pw_hash})

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰에는, payload와 시크릿키가 필요합니다.
        # 시크릿키가 있어야 토큰을 디코딩(=풀기) 해서 payload 값을 볼 수 있습니다.
        # 아래에선 id와 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저ID 값을 알 수 있습니다.
        # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})


# [유저 정보 확인 API]
# 로그인된 유저만 call 할 수 있는 API입니다.
# 유효한 토큰을 줘야 올바른 결과를 얻어갈 수 있습니다.
# (그렇지 않으면 남의 장바구니라든가, 정보를 누구나 볼 수 있겠죠?)
@app.route('/api/nick', methods=['GET'])
def api_valid():
    token_receive = request.cookies.get('mytoken')

    # try / catch 문?
    # try 아래를 실행했다가, 에러가 있으면 except 구분으로 가란 얘기입니다.

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        # 여기에선 그 예로 닉네임을 보내주겠습니다.
        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        return jsonify({'result': 'success', 'nickname': userinfo['nick']})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': '로그인 시간이 만료되었습니다.'})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': '로그인 정보가 존재하지 않습니다.'})

#################################
##  리뷰 작성 및 저장             ##
#################################
@app.route("/review/post", methods=["POST"])
def movie_post():
    name_receive = request.form['name_give']
    star_receive = request.form['star_give']
    comment_receive = request.form['comment_give']

    doc = {'name' : name_receive,
           'star' : star_receive,
           'comment' : comment_receive
           }
    db.reviews.insert_one(doc)

    return jsonify({'msg': '저장 완료'})

@app.route("/review/get", methods=["GET"])
def movie_get():
    reviews_list = list(db.reviews.find({},{'_id':False}))
    return jsonify({'reviews': reviews_list})

@app.route("/test/request_order")
def request_order():
    return render_template('request_order.html')

@app.route("/test/request_partner")
def request_partner():
    return render_template('request_partner.html')

@app.route('/test/enrollPartner', methods=['POST'])
def enrollPartner():
    partner_receive = request.form['partner_give']

    count = list(db.partners.find({}, {'_id': False}))
    num = cal_num(count)

    partner_code = partner_receive + "partner" + str(num)

    doc = {
        "num": num,
        "partner_name": partner_receive,
        "partner_code": partner_code
    }

    db.partners.insert_one(doc)
    return jsonify({"msg": "등록 완료"})

@app.route("/test/findPartner", methods=['POST'])
def findPartner():
    code_receive = request.form["code_give"]
    partner_info = list(db.goods.find({"partner_code": code_receive}, {'_id': False}))

    return jsonify({"goods": partner_info})

@app.route("/test/partnerList")
def partnerList():
    partner_list = list(db.partners.find({}, {"_id": False}))
    return jsonify({"partners": partner_list})

@app.route("/test/goodsEnroll", methods=['POST'])
def goodsEnroll():
    goods_receive = request.form["goods_give"]
    code_receive = request.form["code_give"]
    cnt_receive = request.form["cnt_give"]

    doc = {
        "goods_name": goods_receive,
        "partner_code": code_receive,
        "cnt": cnt_receive
    }

    db.goods.insert_one(doc);
    return jsonify({"msg": "등록 완료"})

@app.route("/test/userEnroll", methods=['POST'])
def userEnroll():
    user_receive = request.form["user_give"]
    menu_receive = request.form["menu_give"]
    phone_receive = request.form["phone_give"]
    address_receive = request.form["address_give"]
    store_receive = request.form["store_give"]

    doc = {
        "user_name": user_receive,
        "user_menu": menu_receive,
        "user_phone": phone_receive,
        "user_address": address_receive,
        "user_store": store_receive
    }
    db.orders.insert_one(doc);
    return jsonify({"msg": "등록 완료"})

@app.route("/bucket", methods=["GET"])
def bucket_get():
    # 음식의 모든 정보를 html로 넘겨준다
    food_list = list(db.menu.find({}, {'_id': False}))

    #차례로 월~일
    week=[0,0,0,0,0,0,0]

    for total in food_list:
        week[0] = week[0] + total['Day']['월']
        week[1] = week[1] + total['Day']['화']
        week[2] = week[2] + total['Day']['수']
        week[3] = week[3] + total['Day']['목']
        week[4] = week[4] + total['Day']['금']
        week[5] = week[5] + total['Day']['토']
        week[6] = week[6] + total['Day']['일']        

    menu_num=[]
    for total in food_list:
        menu_num.append(total['num'])

    # 재료의 모든 정보를 html로 넘겨준다
    ingredient_list = list(db.ingredient.find({}, {'_id': False}))

    return jsonify({'menu': food_list, 'ingredient': ingredient_list, 'week':week, 'menu_num':menu_num})

##메인페이지 구성

#주문하기
@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == 'GET':
        return render_template('order.html')
    else:
        name = request.form["name"]
        store_name = request.form["store_name"]
        email = request.form["email"]
        address = request.form["address"]
        ingredient = request.form["ingredient"]
        num = request.form["num"]

        doc = {
            'name': name,
            'store_name': store_name,
            'email': email,
            'address': address,
            'ingredient': ingredient,
            'num': num,
        }
        db.orders_new.insert_one(doc)

        # 주문한 재료의 양만큼 db에 증가시킨다
        find_ingre = list(db.ingredient.find({'name': ingredient}, {'_id': False}))
        new_num = int(find_ingre[0]['num']) + int(num)
        db.ingredient.update_one({'name': ingredient}, {'$set': {'num': new_num}})

        return render_template('index.html')

@app.route("/order/buy")
def order_buy():
    print(request.form)

#판매량 및 현재 수량
@app.route("/bucket", methods=["POST"])
def bucket_post():
    food_receive = request.form['menu_give']
    day_receive = request.form['day_give']

    # Menu = ['김치찌개', '동태찌개', '부대찌개', '청국장']
    # Week = ['월', '화', '수', '목', '금', '토', '일']
    # # 입력된 음식이 메뉴에 없으면
    # if food_receive not in Menu:
    #     return jsonify({'msg': '메뉴에 없는 음식입니다. 다시 입력하세요'})
    # # 입력된 요일이 잘못돼었으면
    # if day_receive not in Week:
    #     return jsonify({'msg': '요일을 잘못 입력하셨습니다. 다시 입력하세요'})

    # db에서 클라이언트가 준 food_receive(음식)의 정보를 받아온다.
    menu_list = list(db.test_menu.find({'name': food_receive}, {'_id': False}))

    # 만약 음식 정보가 없으면 (처음으로 음식을 입력할 경우)
    if len(menu_list) == 0:

        days = {'월': 0, '화': 0, '수': 0, '목': 0, '금': 0, '토': 0, '일': 0}

        # day_receive(요일)의 맞춰서 밸류값을 증가
        for day in days.keys():
            if day == day_receive:
                days[day] = days[day] + 1
                break

        doc = {
            'name': food_receive,
            'Day': days,
            'num': 1
        }

        db.test_menu.insert_one(doc)

    # 이미 등록된 음식이라면
    else:
        food_ingredient = {'김치찌개': ['마늘', '양파', '대파', '소금'], '청국장': ['양파', '대파'],
                           '부대찌개': ['마늘', '소금'], '동태찌개': ['소금']}

        # food_receive(키값)에 맞는 밸류값들(재료들)을 하나씩 감소시킨다
        for ingredient in food_ingredient[food_receive]:
            find_ingre = list(db.ingredient.find({'name': ingredient}, {'_id': False}))
            new_num = int(find_ingre[0]['num']) - 1
            # 감소된 재료를 db에 업데이트 한다
            db.ingredient.update_one({'name': ingredient}, {'$set': {'num': new_num}})

        ###음식판매 숫자 증가시키기###
        # food_receive(판매된 음식)의 정보를 받아온다
        food = list(db.menu.find({'name': food_receive}, {'_id': False}))
        # 음식의 기존 판매량에 1을 더해줌
        new_num = int(food[0]['num']) + 1

        # 44줄 dictionay값
        day_dic = food[0]['Day']

        # day_dic을 돌려 맞는 요일을 하나 증가시켜줌
        for day in day_dic.keys():
            if day == day_receive:
                day_dic[day] = day_dic[day] + 1
                break
        # 음식의 판매량과 요일의 값을 업데이트
        db.menu.update_one({'name': food_receive}, {'$set': {'num': new_num}})
        db.menu.update_one({'name': food_receive}, {'$set': {'Day': day_dic}})

    return jsonify({'msg': '등록완료'})

#사이드바 href
@app.route('/partner_list')
def partner_list():
    return render_template("partner_list.html")

@app.route('/menu_list')
def menu_list():
    return render_template("menu_list.html")

@app.route('/order_list')
def order_list():
    return render_template("order_list.html")

@app.route('/price_setting')
def price_setting():
    return render_template("price_setting.html")

@app.route('/restaurant_code')
def restaurant_code():
    payload = login_check();
    user_id = payload['id']
    return render_template("restaurant_code.html")

#메뉴 목록
@app.route('/menu_list/menu_enroll', methods=['POST'])
def menu_enroll():
    days = {'월': 0, '화': 0, '수': 0, '목': 0, '금': 0, '토': 0, '일': 0}
    menu_receive = request.form['menu_give']
    payload = login_check()
    menu_check = db.menu.find_one({"user_id": payload['id'], 'menu': menu_receive}, {'_id': False})
    if not menu_check is None:
        return jsonify({"msg": "메뉴가 등록되어있습니다."})
    db.menu.insert_one({'user_id': payload['id'], 'menu': menu_receive,"Day": days, "num":1})
    return jsonify({"msg": "등록 완료"})

@app.route('/menu_list/ingredients_enroll', methods=['POST'])
def ingredients_enroll():
    menu_receive = request.form['menu_give']
    ingredients_receive = request.form['ingre_give']
    count = 0
    payload = login_check()
    ingre_count = db.menu.find_one({"user_id": payload['id'], 'menu': menu_receive},{'_id': False})
    if ingre_count == None:
        return jsonify({"msg": "메뉴가 없습니다."})
    print([ k for k in ingre_count.keys() if 'ingredient_' in k])
    if [ k for k in ingre_count.keys() if 'ingredient_' in k] == []:
        count = 0
    else:
        for a in [ k for k in ingre_count.keys() if 'ingredient_' in k]:
            count += 1

    db.menu.update_one(
        {"user_id": payload['id'], 'menu': menu_receive},
        {"$set" :
             {"ingredient_"+str(count): ingredients_receive}
         },
        True
    )
    return jsonify({"msg": "등록 완료"})

@app.route('/menu_list/menu_show')
def menu_show():
    payload = login_check()
    menu_list = list(db.menu.find({'user_id': payload['id']},{'_id':False}))
    return jsonify({"menu_show": menu_list})

@app.route('/menu_list/menu_delete', methods=['POST'])
def menu_delete():
    menu = request.form['menu_give']
    payload = login_check()
    db.menu.delete_one({"user_id": payload['id'], "menu": menu})
    return jsonify({"msg": "삭제 완료"})

#추가세팅
#식당 코드 설정
@app.route('/addtion_setting/restaurant_enroll', methods=['POST'])
def restaurant_enroll():
    res_receive = request.form['res_give']
    payload = login_check()
    db.user.update_one({'id': payload['id']},{"$set":{"userstore":res_receive}})
    return jsonify({"msg": "등록 완료"})

@app.route('/addition_setting/res_name')
def res_name():
    payload = login_check()
    user_info = db.user.find_one({"id": payload['id']})
    return jsonify({"res_name": user_info['userstore']})

#기능 함수 모음
def cal_num(temp_list):
    if len(temp_list) == 0:
        num = 1
    else:
        temp_num = 0
        for cnt in temp_list:
            if temp_num < cnt['num']:
                temp_num = cnt['num']
        num = temp_num + 1
    return num

def login_check():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)