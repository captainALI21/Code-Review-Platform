-- Active: 1728635196871@@127.0.0.1@3306@questionanswerplatform
-- Most Popular Questions
SELECT Q.QUESTION_ID, Q.TITLE, Q.BODY, Q.VIEWS, Q.UPVOTES, U.USERNAME AS AUTHOR
FROM QUESTIONS Q
JOIN USERS U ON Q.USER_ID = U.USER_ID
ORDER BY Q.UPVOTES DESC, Q.VIEWS DESC
LIMIT 10;

-- Get Answers for a Specific Question
SELECT A.ANSWER_ID, A.BODY, A.CODE, A.UPVOTES, U.USERNAME AS AUTHOR
FROM ANSWERS A
JOIN USERS U ON A.USER_ID = U.USER_ID
WHERE A.QUESTION_ID = 1
ORDER BY A.UPVOTES DESC;

-- Get All Comments for a Specific Question
SELECT C.COMMENT_ID, C.BODY, U.USERNAME AS AUTHOR, C.CREATED_AT
FROM COMMENTS C
JOIN USERS U ON C.USER_ID = U.USER_ID
WHERE C.PARENT_ID = 1 AND C.PARENT_TYPE = 'QUESTION'
ORDER BY C.CREATED_AT ASC;

-- Get Questions by Tag
SELECT Q.QUESTION_ID, Q.TITLE, Q.BODY, Q.UPVOTES, Q.VIEWS, U.USERNAME AS AUTHOR
FROM QUESTIONS Q
JOIN QUESTION_TAGS QT ON Q.QUESTION_ID = QT.QUESTION_ID
JOIN TAGS T ON QT.TAG_ID = T.TAG_ID
JOIN USERS U ON Q.USER_ID = U.USER_ID
WHERE T.TAG_NAME = 'C++'
ORDER BY Q.UPVOTES DESC;

-- Search Questions by Title or Body
SELECT Q.QUESTION_ID, Q.TITLE, Q.BODY, Q.VIEWS, Q.UPVOTES, U.USERNAME AS AUTHOR
FROM QUESTIONS Q
JOIN USERS U ON Q.USER_ID = U.USER_ID
WHERE Q.TITLE LIKE '%linked list%' OR Q.BODY LIKE '%linked list%';

CREATE INDEX idx_user_email ON USERS(EMAIL);
CREATE INDEX idx_question_user ON QUESTIONS(USER_ID);
CREATE INDEX idx_answer_question ON ANSWERS(QUESTION_ID);

GRANT ALL PRIVILEGES ON questionanswerplatform.* TO 'root'@'localhost';
FLUSH PRIVILEGES;

