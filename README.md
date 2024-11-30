## 🍽️ Coupang Eats Clone Project - Backend API

A REST API server project implementing the core functionalities of Coupang Eats.

## **🛠️ Tech Stack**

- Python
- Flask
- MySQL
- PyMySQL

## **🏗️ System Architecture**

## **Database Structure**

- Consists of 8 tables:
    - restaurants: Restaurant information
    - menus: Menu information
    - users: User information
    - restaurant_images: Restaurant images
    - orders: Order information
    - order_items: Order details
    - reviews: Review information
    - wow_promotions: Wow member promotions

## **Views**

- 5 custom views for efficient data retrieval:
    - promotions_view: Current promotions display
    - orders_view: Order details and calculations
    - users_view: User statistics and savings
    - restaurant_stats_view: Restaurant performance metrics
    - menu_analytics_view: Menu performance analysis

## **🌟 Key Features**

## **1. Restaurant Management**

- Restaurant search within 10km radius
- Category-based filtering
- Delivery fee calculation based on distance
- Restaurant details and menu information

## **2. Order System**

- Order creation and management
- Order status tracking
- Order history viewing
- Detailed order calculations including discounts

## **3. User Features**

- User profile management
- Wow membership benefits
- Order history tracking
- Delivery address management

## **4. Review System**

- Review creation and management
- Rating system
- Photo review support
- Review statistics

## **5. Promotion System**

- Wow member exclusive promotions
- Free delivery benefits
- Special event promotions
- Time-limited offers

## **📡 API Endpoints**

- /restaurants: Restaurant listing and details
- /users: User management
- /orders: Order processing
- /reviews: Review management
- /calculate-fee: Delivery fee calculation

This project aims to replicate the core functionalities of Coupang Eats' backend system, providing a comprehensive API for food delivery service operations.
