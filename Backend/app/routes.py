import jwt
import datetime
from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from app.extensions import mysql
from app.models import get_user_by_email, register_user

app_routes = Blueprint('app_routes', __name__)

 

def generate_jwt_token(user_id):
    expiration_time = datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token expires in 1 hour
    payload = {
        'user_id': user_id,
        'exp': expiration_time
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def decode_token():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, "Authorization header missing or invalid"
    
    token = auth_header.split(" ")[1]  
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload, None 
    except jwt.ExpiredSignatureError:
        return None, "Token has expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"

# Login a user
@app_routes.route('/api/users/login', methods=['POST'])
def login():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid or missing JSON data"}), 400

        email = data.get('email')
        password = data.get('password')

        if not all([email, password]):
            return jsonify({"error": "Missing required fields"}), 400

        user = get_user_by_email(email)
        if user and check_password_hash(user[3], password):
            token = generate_jwt_token(user[0])  

            return jsonify({
                "message": "Login successful",
                "user": {
                    "user_id": user[0],
                    "username": user[1],
                    "email": user[2]
                },
                "token": token 
            }), 200

        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Register a new user
@app_routes.route('/api/users/register', methods=['POST'])
def registeruser():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid or missing JSON data"}), 400

        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return jsonify({"error": "Missing required fields"}), 400

        existing_user = get_user_by_email(email)
        if existing_user:
            return jsonify({"error": "Email already in use"}), 400

        password_hash = generate_password_hash(password)

        user_id = register_user(username, email, password_hash)

        created_at = datetime.datetime.utcnow().isoformat()

        return jsonify({
            "message": "User registered successfully",
            "user_id": user_id,
            "username": username,
            "email": email,
            "created_at": created_at
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_routes.route('/api/questions', methods=['GET'])
def get_all_questions():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")
        query = """
            SELECT 
                q.question_id,
                q.title,
                q.body,
                q.created_at,
                q.updated_at,
                q.views,
                q.upvotes,
                u.username AS asked_by
            FROM 
                questions q
            JOIN 
                users u ON q.user_id = u.user_id;
        """
        cursor.execute(query)
        results = cursor.fetchall()

        questions = [
            {
                "question_id": row[0],
                "title": row[1],
                "body": row[2],
                "created_at": row[3],
                "updated_at": row[4],
                "views": row[5],
                "upvotes": row[6],
                "asked_by": row[7]
            }
            for row in results
        ]
        return jsonify({"questions": questions}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_routes.route('/api/questions/<int:question_id>', methods=['GET'])
def get_question_with_details(question_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")  

        query = """
        SELECT 
            q.question_id AS question_id,
            q.title AS question_title,
            q.body AS question_body,
            q.code AS question_code,
            q.created_at AS question_created_at,
            q.updated_at AS question_updated_at,
            q.views AS question_views,
            q.upvotes AS question_upvotes,
            u.username AS question_asked_by,  -- Added username for the question creator
            
            a.answer_id AS answer_id,
            a.body AS answer_body,
            a.code AS answer_code,
            a.created_at AS answer_created_at,
            a.updated_at AS answer_updated_at,
            a.upvotes AS answer_upvotes,
            ua.username AS answer_asked_by,  -- Added username for the answer creator
            
            c.comment_id AS comment_id,
            c.parent_type AS comment_parent_type,
            c.parent_id AS comment_parent_id,
            c.body AS comment_body,
            c.created_at AS comment_created_at,
            c.updated_at AS comment_updated_at,
            uc.username AS comment_posted_by  -- Added username for the comment creator
        FROM 
            questions q
        LEFT JOIN 
            answers a ON q.question_id = a.question_id
        LEFT JOIN 
            comments c ON (
                (c.parent_type = 'question' AND c.parent_id = q.question_id) OR
                (c.parent_type = 'answer' AND c.parent_id = a.answer_id)
            )
        LEFT JOIN
            users u ON q.user_id = u.user_id  -- Join for the question creator
        LEFT JOIN
            users ua ON a.user_id = ua.user_id  -- Join for the answer creator
        LEFT JOIN
            users uc ON c.user_id = uc.user_id  -- Join for the comment creator
        WHERE 
            q.question_id = %s;
        """
        
        cursor.execute(query, (question_id,))
        result = cursor.fetchall()

        if not result:
            return jsonify({"error": "Question not found"}), 404

        response = {
            "question": {
                "question_id": result[0][0],
                "title": result[0][1],
                "body": result[0][2],
                "code": result[0][3],
                "created_at": result[0][4],
                "updated_at": result[0][5],
                "views": result[0][6],
                "upvotes": result[0][7],
                "asked_by": result[0][8],  
            },
            "answers": [],
            "comments": [],
        }

        answers = {} 
        comments = []  

        for row in result:
            if row[8]: 
                answer = {
                    "answer_id": row[8],
                    "body": row[9],
                    "code": row[10],
                    "created_at": row[11],
                    "updated_at": row[12],
                    "upvotes": row[13],
                    "asked_by": row[14],
                    "comments": []
                }
                answers[row[8]] = answer 

            if row[14]: 
                comment = {
                    "comment_id": row[14],
                    "parent_type": row[15],
                    "parent_id": row[16],
                    "body": row[17],
                    "created_at": row[18],
                    "updated_at": row[19],
                    "posted_by": row[20],  
                }
                if row[15] == 'answer' and row[16] in answers:
                    answers[row[16]]["comments"].append(comment)  
                elif row[15] == 'question':
                    comments.append(comment)

        response["answers"] = list(answers.values()) 
        response["comments"] = comments

        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_routes.route('/api/users', methods=['GET'])
def get_user_info():
    payload, error = decode_token()
    
    if error:
        return jsonify({"error": error}), 401  

    user_id_from_token = payload['user_id']  
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")
        
        query = """
        SELECT
            u.user_id,
            u.username,
            u.email,
            u.created_at
        FROM
            users u
        WHERE
            u.user_id = %s;
        """
        cursor.execute(query, (user_id_from_token,))
        result = cursor.fetchone()
        print(result)
        if not result:
            return jsonify({"error": "User not found"}), 404

        user_info = {
            "user_id": result[0],
            "username": result[1],
            "email": result[2],
            "created_at": result[3]
        }
        print(user_info)
        print("Decoded user_id: {user_id_from_token}") 


        return jsonify(user_info), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_routes.route('/api/questions/<int:question_id>', methods=['DELETE'])
def delete_question(question_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform") 

        query = "DELETE FROM questions WHERE question_id = %s"
        
        cursor.execute(query, (question_id,))
        mysql.connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Question not found"}), 404
        
        cursor.close()
        return jsonify({"message": "Question deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_routes.route('/api/tags', methods=['GET'])
def get_all_tags():
    try:
        cursor=mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform") 
        query = "SELECT tag_id, tag_name FROM tags "
        cursor.execute(query)
        mysql.connection.commit()
        results = cursor.fetchall()

        cursor.close()
        if not results:
            return jsonify({"message": "No tags found"}), 404

        tags = [{"tag_id": row[0], "tag_name": row[1]} for row in results]

        return jsonify({"tags": tags}), 200

    except Exception as e:
            return jsonify({"error": str(e)}), 500

@app_routes.route('/api/questions', methods=['GET'])
def get_questions_by_tag():
    try:
        tag_name = request.args.get('tag')

        if not tag_name:
            return jsonify({"error": "Tag name is required"}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")  

        query = """
        SELECT 
            q.question_id,
            q.title,
            q.body,
            q.created_at,
            q.updated_at,
            q.views,
            q.upvotes,
            u.username AS asked_by
        FROM 
            questions q
        JOIN 
            question_tags qt ON q.question_id = qt.question_id
        JOIN 
            tags t ON qt.tag_id = t.tag_id
        JOIN 
            users u ON q.user_id = u.user_id
        WHERE 
            t.tag_name = %s;
        """
        
        cursor.execute(query, (tag_name,))
        results = cursor.fetchall()

        cursor.close()

        if not results:
            return jsonify({"message": "No questions found for this tag"}), 404

        questions = [
            {
                "question_id": row[0],
                "title": row[1],
                "body": row[2],
                "created_at": row[3],
                "updated_at": row[4],
                "views": row[5],
                "upvotes": row[6],
                "asked_by": row[7]
            }
            for row in results
        ]

        return jsonify({"questions": questions}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_routes.route('/api/questions/<int:question_id>/comments', methods=['GET'])
def get_comments_for_question(question_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform") 
        query = """
        SELECT 
            c.comment_id,
            c.parent_type,
            c.parent_id,
            c.body,
            c.created_at,
            c.updated_at,
            u.username AS commented_by
        FROM 
            comments c
        JOIN
            users u ON c.user_id = u.user_id
        WHERE
            c.parent_type = 'question' AND c.parent_id = %s;
        """

        cursor.execute(query, (question_id,))
        result = cursor.fetchall()

        if not result:
            return jsonify({"message": "No comments found for this question"}), 404

        comments = [
            {
                "comment_id": row[0],
                "parent_type": row[1],
                "parent_id": row[2],
                "body": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "commented_by": row[6]
            }
            for row in result
        ]

        return jsonify({"comments": comments}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app_routes.route('/api/uploadquestion', methods=['POST'])
def upload_question():
    try:
        payload, error = decode_token()
        if error:
            return jsonify({"error": error}), 401

        user_id = payload.get("user_id")
        if not user_id:
            return jsonify({"error": "Invalid token"}), 401

        data = request.json
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        title = data.get("title")
        description = data.get("description")
        code_snippet = data.get("code")

        if not title or not description:
            return jsonify({"error": "Title and description are required"}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")
        
        query = """
        INSERT INTO questions (user_id, title, body, code, created_at)
        VALUES (%s, %s, %s, %s, NOW())
        """
        cursor.execute(query, (user_id, title, description, code_snippet))

        mysql.connection.commit()
        print("Commit successful")

        question_id = cursor.lastrowid
        cursor.close()

        return jsonify({"message": "Question submitted successfully", "question_id": question_id}), 201

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

@app_routes.route('/api/getuseridfromtoken', methods=['GET'])
def getuserid():
    try:
        payload, error = decode_token()
        if error:
            return jsonify({"error": error}), 401
        user_id = payload.get("user_id")
        return jsonify({'user_id': user_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app_routes.route('/api/updatequestion/<int:question_id>', methods=['PUT'])
def updatequestion(question_id):
    try:
        payload, error = decode_token()  
        user_id = payload['user_id']   
        
        data = request.json
        if not data:
            return jsonify({"error": "Invalid or missing JSON data"}), 400

        code = data.get('code')
        body = data.get('body')

        if not all([code, body]):
            return jsonify({"error": "Missing required fields"}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")
        
        query = """
        SELECT user_id
        FROM questions
        WHERE question_id = %s;
        """
        cursor.execute(query, (question_id,))
        result = cursor.fetchone()
        
        if not result or user_id != result[0]:
            return jsonify({"error": "Unauthorized user"}), 403
        
        update_query = """
        UPDATE questions
        SET
            code = %s,
            body = %s,
            updated_at = NOW()
        WHERE
            question_id = %s;
        """
        cursor.execute(update_query, (code, body, question_id))
        mysql.connection.commit()

        return jsonify({"message": "Question updated successfully"}), 200
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@app_routes.route('/api/updateanswer/<int:answer_id>', methods=['PUT'])
def updateanswer(answer_id):
    try:
        payload, error = decode_token() 
        user_id = payload['user_id']    
        
        data = request.json
        if not data:
            return jsonify({"error": "Invalid or missing JSON data"}), 400

        code = data.get('code')
        body = data.get('body')

        if not body:
            return jsonify({"error": "Missing required fields"}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")
        
        query = """
        SELECT user_id
        FROM answers
        WHERE answer_id = %s;
        """
        cursor.execute(query, (answer_id,))
        result = cursor.fetchone()
        
        if not result or user_id != result[0]:
            return jsonify({"error": "Unauthorized user"}), 403
        
        update_query = """
        UPDATE answers
        SET
            code = %s,
            body = %s,
            updated_at = NOW()
        WHERE
            answer_id = %s;
        """
        cursor.execute(update_query, (code ,body, answer_id))
        mysql.connection.commit()

        return jsonify({"message": "Answer updated successfully"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@app_routes.route('/api/updatecomment/<int:comment_id>', methods=['PUT'])
def updatecomment(comment_id):
    try:
        payload, error = decode_token()  
        user_id = payload['user_id']   
        
        data = request.json
        if not data:
            return jsonify({"error": "Invalid or missing JSON data"}), 400

        body = data.get('body')

        if not body:
            return jsonify({"error": "Missing required fields"}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")
        
        query = """
        SELECT user_id
        FROM comments
        WHERE comment_id = %s;
        """
        cursor.execute(query, (comment_id,))
        result = cursor.fetchone()
        
        if not result or user_id != result[0]:
            return jsonify({"error": "Unauthorized user"}), 403
        
        update_query = """
        UPDATE comments
        SET
            body = %s,
            updated_at = NOW()
        WHERE
            comment_id = %s;
        """
        cursor.execute(update_query, (body, comment_id))
        mysql.connection.commit()

        return jsonify({"message": "Comment updated successfully"}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@app_routes.route('/api/<int:question_id>/answers', methods=['POST'])
def post_answer(question_id):
    try:
        print(f"Received POST request to post an answer for question ID: {question_id}")
        
        data = request.get_json()
        print(f"Request data: {data}")

        payload, error = decode_token()
        print(f"Decoded token: {payload}, Error: {error}")
        
        if error:
            return jsonify({"error": "Invalid token"}), 401

        user_id = payload['user_id']
        print(f"User ID extracted from token: {user_id}")

        body = data.get("body")
        code = data.get("code", None)  

        if not body:
            print("Answer body is missing")
            return jsonify({"error": "Answer body cannot be empty"}), 400

        print("Attempting to insert answer into the database...")
        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")
        cursor.execute("""
            INSERT INTO answers (question_id, user_id, body, code, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (question_id, user_id, body, code))
        mysql.connection.commit()
        print("Answer inserted successfully!")

        return jsonify({"message": "Answer posted successfully"}), 201
    except Exception as e:
        print(f"Error occurred in post_answer: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app_routes.route('/api/comments/<parent_type>/<int:parent_id>', methods=['POST'])
def post_comment(parent_type, parent_id):
    try:
        payload, error = decode_token()
        user_id = payload['user_id']
        data = request.get_json()
        body = data.get("body")

        if not body:
            return jsonify({"error": "Comment body cannot be empty"}), 400

        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")
        cursor.execute("""
            INSERT INTO comments (parent_type, parent_id, user_id, body, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """, (parent_type, parent_id, user_id, body))
        mysql.connection.commit()

        return jsonify({"message": "Comment posted successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_routes.route('/api/user/myquestions', methods=['GET'])
def get_user_questions():
    try:
        payload, error = decode_token()
        user_id = payload['user_id']
        # Establish a database connection
        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform") 

        query = """
        SELECT 
            q.question_id,
            q.title,
            q.body,
            q.created_at,
            q.updated_at,
            q.upvotes,
            u.username AS asked_by
        FROM 
            questions q
        JOIN 
            users u ON q.user_id = u.user_id
        WHERE 
            q.user_id = %s;
        """

        cursor.execute(query, (user_id,))
        
        result = cursor.fetchall()

        if not result:
            return jsonify({"error": "No questions found for this user"}), 404

        questions = []
        for row in result:
            questions.append({
                "question_id": row[0],
                "title": row[1],
                "body": row[2],
                "created_at": row[3],
                "updated_at": row[4],
                "upvotes": row[5],
                "asked_by": row[6],
            })

        return jsonify({"questions": questions}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app_routes.route('/api/my-answered-questions', methods=['GET'])
def get_answered_questions():
    try:
        payload, error = decode_token()
        user_id = payload['user_id']

        cursor = mysql.connection.cursor()
        cursor.execute("USE questionanswerplatform")  

        
        cursor.execute("""
            SELECT 
                q.question_id,
                q.title,
                q.body,
                q.code,
                q.created_at,
                q.updated_at,
                a.answer_id,
                a.body AS answer_body,
                a.created_at AS answer_created_at
            FROM questions q
            JOIN answers a ON q.question_id = a.question_id
            WHERE a.user_id = %s
        """, (user_id,))
        
        result = cursor.fetchall()
        
        if not result:
            return jsonify({"message": "You haven't answered any questions."}), 200
        
        questions = []
        for row in result:
            question = {
                "question_id": row[0],
                "title": row[1],
                "body": row[2],
                "code": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "answer": {
                    "answer_id": row[6],
                    "body": row[7],
                    "created_at": row[8]
                }
            }
            questions.append(question)
        
        return jsonify(questions), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
