import pymysql
from flask import Flask, request, jsonify
from datetime import datetime
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'qwaszx1415!',
    'db': 'coupangeats',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

# 1. /restaurants - 10km 이내의 레스토랑 조회
@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT latitude, longitude, is_wow_member
                FROM users 
                WHERE user_id = %s
            """, (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"error": "User not found"}), 404

            cursor.execute("""
                WITH DistanceCalculation AS (
                    SELECT r.id, r.name, r.cook_time, r.three_km_fee, r.five_km_fee, 
                        r.ten_km_fee, r.over_ten_km_fee, w.event_description,
                        ROUND(
                            ST_Distance_Sphere(
                                POINT(r.longitude, r.latitude), 
                                POINT(%s, %s)
                            ) / 1000, 1
                        ) AS distance_km,
                        rev.rating,
                        rev.review_id,
                        ri.image_url
                    FROM restaurants r
                    LEFT JOIN wow_promotions w ON r.id = w.restaurant_id
                    LEFT JOIN reviews rev ON r.id = rev.restaurant_id
                    LEFT JOIN restaurant_images ri ON r.id = ri.restaurant_id
                    WHERE (w.valid_until IS NULL OR w.valid_until >= CURRENT_TIMESTAMP)
                )
                SELECT 
                    id, 
                    name,
                    distance_km,
                    CAST(cook_time + (distance_km * 1.5) + 5 AS SIGNED) AS delivery_time,
                    CASE 
                        WHEN event_description = 'NULL' THEN '매 주문 무료배달 적용 매장' 
                        ELSE CONCAT('무료배달 + ', event_description) 
                    END AS promotion,
                    ROUND(AVG(rating), 1) as average_rating,
                    COUNT(review_id) as total_reviews,
                    MIN(image_url) as restaurant_image,
                    CASE
                        WHEN %s = TRUE THEN '무료배달'
                        ELSE 
                            CASE
                                WHEN distance_km <= 3 THEN three_km_fee
                                WHEN distance_km <= 5 THEN five_km_fee
                                WHEN distance_km <= 10 THEN ten_km_fee
                                ELSE over_ten_km_fee 
                            END
                    END AS delivery_fee
                FROM DistanceCalculation
                GROUP BY id, name, distance_km, cook_time, event_description, 
                        three_km_fee, five_km_fee, ten_km_fee, over_ten_km_fee
                HAVING distance_km <= 10
                ORDER BY distance_km
            """, (user['longitude'],
                  user['latitude'],
                  user['is_wow_member']))
            
            restaurants = cursor.fetchall()
            return jsonify(restaurants), 200
    finally:
        conn.close()

# 2. /restaurants/<int:restaurant_id> - 특정 레스토랑 조회
@app.route('/restaurants/<int:restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    conn = None
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT latitude, longitude 
                FROM users 
                WHERE user_id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                return jsonify({"error": "User not found"}), 404

            cursor.execute("""
                WITH DistanceCalculation AS (
                    SELECT r.id, r.name, r.address, r.min_order_amount, r.cook_time,
                        r.three_km_fee, r.five_km_fee, r.ten_km_fee, r.over_ten_km_fee,
                        ROUND(
                            ST_Distance_Sphere(
                                POINT(r.longitude, r.latitude), 
                                POINT(%s, %s)
                            ) / 1000, 1
                        ) AS distance_km,
                        w.event_description,
                        rev.rating, rev.review_id,
                        m.name as menu_name,
                        ri.image_url
                    FROM restaurants r
                    LEFT JOIN wow_promotions w ON r.id = w.restaurant_id
                    LEFT JOIN reviews rev ON r.id = rev.restaurant_id
                    LEFT JOIN menus m ON r.id = m.restaurant_id
                    LEFT JOIN restaurant_images ri ON r.id = ri.restaurant_id
                    WHERE r.id = %s
                    AND (w.valid_until IS NULL OR w.valid_until >= CURRENT_TIMESTAMP)
                )
                SELECT 
                    id, name, address, min_order_amount, cook_time,
                    distance_km,
                    CAST(cook_time + (distance_km * 1.5) + 5 AS SIGNED) AS delivery_time,
                    CASE WHEN event_description = 'NULL' THEN '매 주문 무료배달 적용 매장' 
                        ELSE CONCAT('무료배달 + ', event_description) 
                    END AS promotion,
                    ROUND(AVG(rating), 1) as average_rating,
                    COUNT(review_id) as total_reviews,
                    GROUP_CONCAT(DISTINCT menu_name) as menu_items,
                    GROUP_CONCAT(DISTINCT image_url) as restaurant_images,
                    CASE
                        WHEN %s = TRUE THEN '무료배달'
                        ELSE 
                            CASE
                                WHEN distance_km <= 3 THEN three_km_fee
                                WHEN distance_km <= 5 THEN five_km_fee
                                WHEN distance_km <= 10 THEN ten_km_fee
                                ELSE over_ten_km_fee 
                            END
                    END AS delivery_fee
                FROM DistanceCalculation
                GROUP BY id, name, address, min_order_amount, cook_time, distance_km,
                        event_description, three_km_fee, five_km_fee, ten_km_fee, over_ten_km_fee
            """, (user['longitude'],
                  user['latitude'],
                  restaurant_id,
                  user.get('is_wow_member', False)))
            
            restaurant = cursor.fetchone()
            
            if not restaurant:
                return jsonify({"error": "Restaurant not found"}), 404

            if restaurant.get('menu_items'):
                restaurant['menu_items'] = restaurant['menu_items'].split(',')
            if restaurant.get('restaurant_images'):
                restaurant['restaurant_images'] = restaurant['restaurant_images'].split(',')
                
            return jsonify(restaurant), 200
        
    finally:
        if conn is not None:
            conn.close()

# 3. /users - 모든 사용자 조회
@app.route('/users', methods=['GET'])
def get_users():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users_view")
            users = cursor.fetchall()
            return jsonify(users), 200
    finally:
        conn.close()

# 4. /users/<int:user_id> - 특정 사용자 조회
@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM users_view WHERE user_id = %s
            """, (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"error": "User not found"}), 404
            return jsonify(user), 200
    finally:
        conn.close()

# 5. /calculate-fee - 배달비 계산
@app.route('/calculate-fee', methods=['GET'])
def calculate_fee():
    try:
        restaurant_id = request.args.get('restaurant_id', type=int)
        user_id = request.args.get('user_id', type=int)

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    CASE
                        WHEN distance_km <= 3 THEN 2000
                        WHEN distance_km <= 5 THEN 3000
                        WHEN distance_km <= 10 THEN 4000
                        ELSE -1
                    END AS delivery_fee
                FROM (
                    SELECT 
                        ROUND(
                            ST_Distance_Sphere(
                            POINT(r.longitude, r.latitude),
                            POINT(u.longitude, u.latitude)
                            ) / 1000
                        ,1) AS distance_km
                    FROM restaurants r, users u
                    WHERE r.id = %s AND u.user_id = %s
                ) AS dist
            """, (restaurant_id, user_id))
            
            result = cursor.fetchone()
            return jsonify(result), 200
    finally:
        conn.close()

# 6. /orders - 모든 주문 조회
@app.route('/orders', methods=['GET'])
def get_orders():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM orders_view")
            orders = cursor.fetchall()
            return jsonify(orders), 200
    finally:
        conn.close()

# 7. /orders/<int:order_id> - 특정 주문 조회
@app.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM orders_view WHERE order_id = %s
            """, (order_id,))
            order = cursor.fetchone()
            
            if not order:
                return jsonify({"error": "Order not found"}), 404
            return jsonify(order), 200
    finally:
        conn.close()

@app.route('/reviews', methods=['GET'])
def get_reviews():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT r.*,
                    user_reviews.review_count,
                    ROUND(user_reviews.user_avg_ratings, 1) as user_avg_ratings,
                    CASE
                        WHEN r.review_image_url != 'null' THEN '포토리뷰'
                        ELSE '일반리뷰'
                    END AS review_type,
                    CASE 
                        WHEN TIMESTAMPDIFF(DAY, r.created_at, now()) < 30 
                            THEN CONCAT(ABS(DATEDIFF(now(), r.created_at)), '일 전')
                        WHEN TIMESTAMPDIFF(MONTH, r.created_at, now()) < 12
                            THEN CONCAT(TIMESTAMPDIFF(MONTH, r.created_at, now()), '개월 전')
                        ELSE CONCAT(TIMESTAMPDIFF(YEAR, r.created_at, now()), '년 전')
                    END as review_time
                FROM reviews r
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as review_count, AVG(rating) as user_avg_ratings
                    FROM reviews
                    GROUP BY user_id
                ) user_reviews ON r.user_id = user_reviews.user_id
            """)
            reviews = cursor.fetchall()
            return jsonify(reviews), 200
    finally:
        conn.close()


# 9. /restaurants/<int:restaurant_id>/reviews - 특정 레스토랑 리뷰 조회
@app.route('/restaurants/<int:restaurant_id>/reviews', methods=['GET'])
def get_restaurant_reviews(restaurant_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT r.*,
                    user_reviews.review_count,
                    CONCAT(SUBSTRING(u.username, 1, 1), '**') AS masked_name,
                    ROUND(user_reviews.user_avg_ratings, 1) as user_avg_ratings,
                    CASE
                        WHEN r.review_image_url != 'null' THEN '포토리뷰'
                        ELSE '일반리뷰'
                    END AS review_type,
                    CASE 
                        WHEN TIMESTAMPDIFF(DAY, r.created_at, now()) < 30 
                            THEN CONCAT(ABS(DATEDIFF(now(), r.created_at)), '일 전')
                        WHEN TIMESTAMPDIFF(MONTH, r.created_at, now()) < 12
                            THEN CONCAT(TIMESTAMPDIFF(MONTH, r.created_at, now()), '개월 전')
                        ELSE CONCAT(TIMESTAMPDIFF(YEAR, r.created_at, now()), '년 전')
                    END as review_time
                FROM reviews r
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as review_count, avg(rating) as user_avg_ratings
                    FROM reviews
                    GROUP BY user_id
                ) user_reviews ON r.user_id = user_reviews.user_id
                JOIN users u ON r.user_id = u.user_id
                WHERE r.restaurant_id = %s
            """, (restaurant_id,))
            reviews = cursor.fetchall()
            return jsonify(reviews), 200
    finally:
        conn.close()

# 10. /restaurants/<int:restaurant_id>/reviews - 리뷰 추가
@app.route('/restaurants/<int:restaurant_id>/reviews', methods=['POST'])
def add_review(restaurant_id):
    try:
        data = request.get_json()
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO reviews (restaurant_id, user_id, rating, review_image_url, content)
                VALUES (%s, %s, %s, %s, %s)
            """, (restaurant_id, data['user_id'], data['rating'], data['review_image_url'], data['content']))
            conn.commit()
            return jsonify({"message": "Review added successfully"}), 201
    finally:
        conn.close()

# 11. /restaurants/<int:restaurant_id>/reviews/<int:review_id> - 리뷰 삭제
@app.route('/restaurants/<int:restaurant_id>/reviews/<int:review_id>', methods=['DELETE'])
def delete_review(restaurant_id, review_id):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM reviews 
                WHERE restaurant_id = %s AND review_id = %s
            """, (restaurant_id, review_id))
            conn.commit()
            
            if cursor.rowcount == 0:
                return jsonify({"error": "Review not found"}), 404
            return jsonify({"message": "Review deleted successfully"}), 200
    finally:
        conn.close()

# 12. /orders - 주문 생성
@app.route('/orders', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        current_time = datetime.now()
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO orders (user_id, restaurant_id, order_status, order_time)
                VALUES (%s, %s, %s, %s)
            """, (data['user_id'], data['restaurant_id'], 'Pending', current_time))
            
            order_id = cursor.lastrowid
            
            for item in data['order_items']:
                cursor.execute("""
                    INSERT INTO order_items (order_id, menu_id, quantity)
                    VALUES (%s, %s, %s)
                """, (order_id, item['menu_id'], item['quantity']))
            
            conn.commit()
            return jsonify({
                "message": "Order created successfully", 
                "order_id": order_id
            }), 201
    finally:
        conn.close()

# 13. /orders/<int:order_id> - 주문 삭제
@app.route('/orders/<int:order_id>', methods=['DELETE'])
def delete_order(order_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT order_id, order_status FROM orders WHERE order_id = %s", (order_id,))
            order = cursor.fetchone()
            
            if not order:
                return jsonify({"error": "Order not found"}), 404
            
            cursor.execute("DELETE FROM orders WHERE order_id = %s", (order_id,))
            conn.commit()
            
            return jsonify({"message": f"Order {order_id} deleted successfully"}), 200
            
    except Exception as e:
        print(f"Error: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
        
    finally:
        if conn:
            conn.close()

# 14. /restaurants/category/<string:category> - 카테고리별 리스트
@app.route('/restaurants/category/<string:category>', methods=['GET'])
def get_restaurants_by_category(category):
    try:
        user_id = request.args.get('user_id', type=int)
        if not user_id:
            return jsonify({"error": "User ID is required"}), 400
            
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT latitude, longitude, is_wow_member
                FROM users 
                WHERE user_id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            if not user:
                return jsonify({"error": "User not found"}), 404

            cursor.execute("""
                WITH DistanceCalculation AS (
                    SELECT r.id, r.name, r.three_km_fee, r.five_km_fee, 
                        r.ten_km_fee, r.over_ten_km_fee, r.cook_time, w.event_description,
                        ROUND(
                            ST_Distance_Sphere(
                                POINT(r.longitude, r.latitude), 
                                POINT(%s, %s)
                            ) / 1000, 1
                        ) AS distance_km,
                        rev.rating,
                        rev.review_id,
                        ri.image_url
                    FROM restaurants r
                    LEFT JOIN wow_promotions w ON r.id = w.restaurant_id
                    LEFT JOIN reviews rev ON r.id = rev.restaurant_id
                    LEFT JOIN restaurant_images ri ON r.id = ri.restaurant_id
                    WHERE r.category = %s
                    AND (w.valid_until IS NULL OR w.valid_until >= CURRENT_TIMESTAMP)
                )
                SELECT 
                    id, 
                    name,
                    distance_km,
                    CAST(cook_time + (distance_km * 1.5) + 5 AS SIGNED) AS delivery_time,
                    CASE WHEN event_description = 'NULL' THEN '매 주문 무료배달 적용 매장' 
                        ELSE CONCAT('무료배달 + ', event_description) 
                    END AS promotion,
                    ROUND(AVG(rating), 1) as average_rating,
                    COUNT(review_id) as total_reviews,
                    MIN(image_url) as restaurant_image,
                    CASE
                        WHEN %s = TRUE THEN '무료배달'
                        ELSE 
                            CASE
                                WHEN distance_km <= 3 THEN three_km_fee
                                WHEN distance_km <= 5 THEN five_km_fee
                                WHEN distance_km <= 10 THEN ten_km_fee
                                ELSE over_ten_km_fee 
                            END
                    END AS delivery_fee
                FROM DistanceCalculation
                GROUP BY id, name, distance_km, cook_time, event_description,
                        three_km_fee, five_km_fee, ten_km_fee, over_ten_km_fee
                HAVING distance_km <= 10
                ORDER BY distance_km
            """, (user['longitude'],
                  user['latitude'],
                 category,
                 user.get('is_wow_member', False)))
            restaurants = cursor.fetchall()
            
            if not restaurants:
                return jsonify({
                    "message": f"카테고리 '{category}'에 해당하는 레스토랑이 없습니다."
                }), 404
                
            return jsonify(restaurants), 200
            
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=1234)
