# MiniTwitter
Program was created based on the functionality of the Twitter platform. Application has server and client side. Client can send messages to the server and request displaying chosen numer of recent posts. Protocol Buffers and gRPC were used for communiaction between server and the client. MongoDB was used for storing messages and Flask was utilised for web development.

## Functionalities
- logging in with a chosen usename
- sending mesages with optional file attachments
- retrieving a specified numer of messages
- adding likes
- adding comments
- retriving an attachment based on its ID


## Getting Started

Follow these steps to set up and run the MiniTwitter project on your local machine.

### Prerequisites

- Git
- Python 3
- Docker

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/Jula143/MiniTwitter
    cd MiniTwitter
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Pull the MongoDB Docker image:
    ```bash
    docker pull mongo
    ```

4. Run the MongoDB container:
    ```bash
    docker run -d -p 27017:27017 --name mongodb mongo
    ```

5. Run the server:
    ```bash
    python server.py
    ```

6. Run the Flask application:
    ```bash
    python app.py
    ```

### Usage
- Access the MiniTwitter web application by navigating to [http://localhost:5000/](http://localhost:5000/) in your web browser.

