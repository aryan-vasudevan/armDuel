#include <WiFi.h>
#include "ESP32Servo.h"
#include "playerMove.cpp"
#include <string>

// const char* ssid = "network name";
// const char* password = "network password";

WiFiServer server(12345);

// Servo settings
Servo playerServo;
int servoPin = 13;
int playerPos = 90;              // Start in middle
int stepForward = 2;             // Auto push forward step

// Servo moves forward every 100ms
unsigned long lastMoveTime = 0;
unsigned long moveInterval = 100;

void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    }

    // Log WiFi
    Serial.println();
    Serial.print("Connected to WiFi\nIP: ");
    Serial.println(WiFi.localIP());

    // Log server
    server.begin();
    Serial.println("Server started on port 12345");

    // Servo
    playerServo.attach(servoPin);
    playerServo.write(playerPos);
}

void loop() {
    WiFiClient client = server.accept();

    if (client) {
        Serial.println("Client connected");

        while (client.connected()) {
            // 1 player mode resistance
            // unsigned long now = millis();
            // if (now - lastMoveTime >= moveInterval) {
            //     lastMoveTime = now;
            //     if (playerPos < 180) {
            //         playerPos += stepForward;
            //         playerServo.write(playerPos);
            //         Serial.println(playerPos);
            //     }
            // }

            // Handle incoming command
            if (client.available()) {
                String command = client.readStringUntil('\n');
                command.trim();

                Serial.print("Received: ");
                Serial.println(command);

                playerMove(command);

                client.flush();
            }

            delay(10);
        }

        Serial.println("Client disconnected");
        client.stop();  // only stop if the client disconnects itself
    }
}
