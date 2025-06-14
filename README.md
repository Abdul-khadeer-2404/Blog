# Blog
# Blog

## Description

This project is a full-stack blogging application that allows users to create, read, update, and delete blog posts. It includes user authentication and profile management features. The application is built using a React frontend and a Flask backend with a SQLite database.

## Features

-   **User Authentication:** Secure registration and login using JWT.
-   **Profile Management:** Users can create and edit their profiles, including uploading a profile picture and adding a bio.
-   **Post Management:** Users can create, edit, and delete their own blog posts.
-   **Like Posts:** Users can like and unlike blog posts.
-   **Responsive Design:** The frontend is built with Tailwind CSS for a responsive and modern look.
-   **Image Uploads:** Profile pictures are uploaded and stored in the backend.

## Technologies Used

-   **Frontend:**
    -   React
    -   React Router
    -   Tailwind CSS
    -   Axios
    -   [lucide-react](https://lucide.dev/)
-   **Backend:**
    -   Flask
    -   Flask-SQLAlchemy
    -   Flask-CORS
    -   Flask-JWT-Extended
    -   Werkzeug
-   **Database:**
    -   SQLite


## Setup Instructions

### Backend

1.  Navigate to the `backend/` directory:

    ```sh
    cd backend
    ```

2.  Create a virtual environment:

    ```sh
    python -m venv venv
    ```

3.  Activate the virtual environment:

    -   On Windows:

        ```sh
        .\venv\Scripts\activate
        ```

    -   On macOS and Linux:

        ```sh
        source venv/bin/activate
        ```

4.  Install the required Python packages:

    ```sh
    pip install -r requirements.txt
    ```

5.  Run the Flask application:

    ```sh
    python app.py
    ```

### Frontend

1.  Navigate to the `frontend/` directory:

    ```sh
    cd ../frontend
    ```

2.  Install the required Node packages:

    ```sh
    npm install
    ```

3.  Start the React development server:

    ```sh
    npm start
    ```

## Configuration

-   **Backend:**
    -   The Flask backend connects to a SQLite database named `blog.db` located in the `backend/` directory.
    -   The JWT secret key is set in the `app.py` file.  **Important:** Change this in production.
    -   The upload folder for profile pictures is `backend/uploads`.
-   **Frontend:**
    -   The frontend communicates with the backend API at `http://localhost:5000`.  Ensure the backend is running on this address.

## Notes

-   The backend includes detailed logging for debugging purposes.
-   The frontend uses local storage to store the JWT token and user information.
-   Error handling is implemented in both the frontend and backend.
-   The application uses CORS to allow cross-origin requests between the frontend and backend.

## Future Enhancements

-   Implement password reset functionality.
-   Add pagination to the blog posts.
-   Implement search functionality.
-   Add comments to blog posts.
-   Implement more robust error handling and validation.
-   Deploy the application to a production environment.