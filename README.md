-----

# 📖 Whook: Self-Hosted Webhook Manager

Whook is a straightforward, self-hosted webhook management and server solution. It allows you to generate unique URLs to receive webhooks, log incoming payloads, and optionally forward them to a destination URL with JSON transformation capabilities.

-----

## ✨ Features

  * **Self-Hosted:** Full control over your data and environment.
  * **Unique Webhook URLs:** Easily generate distinct endpoints for various services.
  * **Payload Logging:** Stores all incoming webhook payloads for review and debugging.
  * **Payload Forwarding:** Route received webhooks to a specified destination URL.
  * **JSON Transformation:** Customize webhook payloads before forwarding using user-defined code.
  * **Simple Interface:** Intuitive design for quick setup and management.

-----

## 🚀 Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

  * UV (https://docs.astral.sh/uv/getting-started/installation/) with or without python if you know how to install python using UV.
  * [Garnet](https://github.com/microsoft/garnet) if you are on Windows or [Redis](https://github.com/redis/redis) server running.

### Installation & Running

```uv venv && source .venv/bin/activate```

```uv add -r requirements.txt```

```./run.sh```

## 🛠️ Usage

### Creating a Webhook Endpoint

Once Whook is running, you can create new webhook endpoints through its web interface. Each endpoint will have a unique URL.

### Receiving Webhooks

Send your webhook payloads to the generated unique URL. Whook will automatically log the incoming request, including headers and payload.

### Configuring Payload Forwarding

For each webhook endpoint, you can specify a **destination URL**. When a webhook is received, Whook will forward the payload to this destination.

### JSON Transformation

Whook allows you to define custom code (e.g., Python functions) to transform the incoming JSON payload before it's forwarded. This is incredibly useful for adapting payloads to the requirements of different destination services.

**Example Transformation Code (Conceptual):**

```javascript// This is an example. The actual implementation will depend on Whook's UI/API.

```

-----



## 🤝 Contributing

Contributions are welcome\! If you'd like to contribute, please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/AmazingFeature`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
5.  Push to the branch (`git push origin feature/AmazingFeature`).
6.  Open a Pull Request.

-----

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

-----

## ❓ Support

If you have any questions or encounter issues, please open an issue on the GitHub repository.

-----
