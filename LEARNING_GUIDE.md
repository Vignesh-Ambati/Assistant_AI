# The Beginner's Guide to AI Assistant

Welcome! If you have zero coding experience and want to understand what this project actually is and how it works, you are in the right place. 

Think of this document as a map. We are going to break down all the scary tech jargon into simple analogies, and then point out exactly where to look in the code to see it in action.

---

## 1. The Big Picture: A Restaurant Analogy
Imagine a busy restaurant.
- **The Customer:** You, using the app on your computer.
- **The Waiter (Frontend):** Takes your order and brings you your food.
- **The Kitchen (Backend API):** Receives the order from the waiter, does all the cooking, and passes the food back.
- **The Pantry (Database):** Where all the ingredients (data and chat history) are stored safely.
- **The Master Chef (AI/Ollama):** The genius who actually knows how to cook up complex answers.
- **The Restaurant Building (Docker):** The physical structure that keeps the kitchen and pantry isolated, organized, and running smoothly, no matter what city it's built in.

Our project follows this exact structure.

---

## 2. What are Coding Languages?
Code is just a set of instructions written in a language that a computer can understand. In this project, we use a few different ones:

1.  **Python (`.py` files)**: Think of Python as plain, readable English. It’s great for complex logic, processing data, and talking to AI. We use it for our **Kitchen (Backend)**.
2.  **TypeScript/JavaScript (`.ts`, `.tsx`, `.js` files)**: The languages of the web. They are used to make things look pretty and interactive on your screen. We use this for our **Waiter (Frontend)**.
3.  **HTML & CSS (`.html`, `.css`)**: HTML is the skeleton (buttons, text boxes), and CSS is the paint and clothing (colors, spacing, fonts).

---

## 3. The Waiter: The Frontend (Electron + React)
The frontend is the visual app you see on your screen.
*   **React:** A tool that lets us build user interfaces using reusable LEGO blocks called "Components".
    *   👉 *Look at `client/src/App.tsx`. This file is the main screen of the app. If you scroll through it, you can actually see the code for the Chat bubbles, the "Send" button, and the text box.*
*   **Tailwind CSS:** A fast way to add colors and spacing by just typing simple words like `bg-blue-500` or `rounded-lg`.
    *   👉 *Look inside `client/src/App.tsx`. You'll see words like `text-white` or `bg-bgDark`. That's Tailwind styling the app.*
*   **Electron:** Normally, React only runs inside a web browser (like Chrome or Safari). Electron is a magic wrapper that packages a web page into a real Windows/Mac desktop application. It allows us to make the app "Always on Top" and remove the ugly browser search bar.
    *   👉 *Look at `client/main.cjs`. This is the Electron file that creates the borderless floating desktop window.*

---

## 4. The Kitchen: The Backend API (FastAPI)
"API" stands for Application Programming Interface. It is simply a digital menu. It gives the Waiter (Frontend) a strict list of things it is allowed to ask the Kitchen to do.
*   **FastAPI:** A very fast Python framework for building APIs.
    *   👉 *Look at `api/app/routers/chat.py`. This file is the "Chef's Station" for chatting. When the frontend sends a message, it lands here.*
*   **Streaming:** When you ask ChatGPT a question, the text appears word-by-word. This is called "Streaming". Instead of making you wait 10 seconds for the whole paragraph, our kitchen sends the food out one bite at a time. 
    *   👉 *Look at `api/app/services/ollama.py`. You'll see code reading chunks of data and "yielding" them back to the user instantly.*

---

## 5. The Master Chef: Local AI (Ollama)
Ollama is a program that runs AI models (like `qwen2.5-coder`) directly on your computer's Graphics Card (GPU) instead of relying on the internet.
*   The Backend (FastAPI) talks to Ollama behind the scenes, asking it to generate a response, and then passes that response to your screen.
*   If we tried to load an AI model that was too big for your graphics card, Ollama would crash. That's why we control its memory usage.

---

## 6. The Pantry: The Database (PostgreSQL)
A database is a giant, highly organized Excel spreadsheet. If you close the app and reopen it, we want your chat history to still be there.
*   **PostgreSQL:** A very powerful database system.
*   **Migrations (Alembic):** As we add features to the app (like adding a "Title" to a chat), the spreadsheet columns need to be updated. Migrations are automatic scripts that upgrade the database safely.
    *   👉 *Look at `api/app/models/database.py`. You will see Python code defining what a `Message` looks like (it has an ID, content, and the time it was created). Alembic turns this Python code into real Database tables.*

---

## 7. The Building: Docker
Imagine you buy a complex Ikea furniture set. Putting it together is a nightmare. What if Ikea just shipped you the entire pre-built room in a shipping container?
That is **Docker**.
Instead of forcing you to manually install Python, PostgreSQL, Redis, and configure them to talk to each other, we wrote a `docker-compose.yml` blueprint.
*   When you run the app, Docker downloads pre-built "Containers" (one for the database, one for the backend) and turns them on simultaneously. They run isolated from your main computer, meaning they can't break your Windows setup.
    *   👉 *Look at `docker-compose.yml`. You'll see it clearly lists the "services" we need: `api`, `postgres`, `redis`, and `celery-worker`.*

---

## 8. Putting it all together (`main.py`)
Because this project has a Frontend, a Backend, a Database, and an AI, starting them all manually would require opening 5 different terminal windows and typing 5 different commands.
*   👉 *Look at `main.py`. This is our "Master Switch". It is a Python script that automatically checks if Docker and Ollama are running, installs any missing files, turns on the Kitchen (Backend), and opens the Waiter (Desktop App) in one single click.*

**Happy Learning!** The best way to learn to code is to break things. Try changing a color in `App.tsx` or altering a printed word in `main.py` and see what happens!
