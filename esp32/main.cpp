#include <WiFi.h>
#include "ESP32Servo.h"
#include <cmath>

// const char* ssid = "network name";
// const char* password = "network password";

WiFiServer server(12345);

// Servo + game state
Servo playerServo;
int servoPin = 13;
int playerPos = 90;       
const int DELTA = 15;     
bool gameEnd = false;
bool greenWon = false;
int buzzerPin = 4;

// LEDs
int redLEDPins[6]   = {12,14,26,25,33,32};
int greenLEDPins[6] = {22,21,19,18,17,16};

int numRedOn = 0;
int numGreenOn = 0;

// Blink timing
unsigned long lastBlinkTime = 0;
int blinkInterval = 500;
bool ledState = false;

void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected, IP: " + WiFi.localIP());

    server.begin();
    Serial.println("Server listening on port 12345");

    // Setup servo
    playerServo.attach(servoPin);
    playerServo.write(playerPos);

    // Setup pins
    pinMode(buzzerPin, OUTPUT);
    for (int i = 0; i < 6; i++) {
        pinMode(redLEDPins[i], OUTPUT);
        pinMode(greenLEDPins[i], OUTPUT);
    }
}

void loop() {
    WiFiClient client = server.accept();
    if (client) {
        Serial.println("Client connected");

        while (client.connected() && !gameEnd) {
            if (client.available()) {
                String cmd = client.readStringUntil('\n');
                cmd.trim();
                Serial.println("Cmd: " + cmd);

                if (cmd == "MOVE_PLAYER_A") {
                    playerPos = max(playerPos - DELTA, 0);
                    playerServo.write(playerPos);
                    client.println("OK");
                }
                else if (cmd == "MOVE_PLAYER_B") {
                    playerPos = min(playerPos + DELTA, 180);
                    playerServo.write(playerPos);
                    client.println("OK");
                }
                else if (cmd == "RESET") {
                    playerPos = 90;
                    playerServo.write(playerPos);
                    gameEnd = false;
                    client.println("OK");
                }
                else {
                    client.println("ERR");
                }

                // Check win thresholds
                if (playerPos <= 15) {
                    gameEnd = true;
                    greenWon = true;
                    Serial.println("GREEN WINS!");
                    client.println("WIN_GREEN");
                }
                else if (playerPos >= 165) {
                    gameEnd = true;
                    greenWon = false;
                    Serial.println("RED WINS!");
                    client.println("WIN_RED");
                }

                client.flush();
            }

            // Always update LEDs/blink
            updateLEDs();
        }

        client.stop();
        Serial.println("Client disconnected");
    } else {
        // no client connected: keep blinking LEDs
        updateLEDs();
        Serial.println(playerPos);
    }
}

// Updates LEDs each loop:
void updateLEDs() {
    unsigned long now = millis();

    if (gameEnd) {
    static unsigned long lastFlash = 0;
        if (now - lastFlash > 250) {
            lastFlash = now;
            ledState = !ledState;
            for (int i = 0; i < 6; i++) {
                digitalWrite(greenLEDPins[i], greenWon && ledState);
                digitalWrite(redLEDPins[i],   !greenWon && ledState);
            }
            digitalWrite(buzzerPin, ledState);
        }
    return;
    }

    // Compute how many LEDs to light
    numGreenOn = (180 - playerPos) / 30; 
    numRedOn   = 6 - numGreenOn;

    // Map distance from center to blink interval
    int distance = abs(playerPos - 90);
    blinkInterval = map(distance, 0, 90, 800, 200);

    // Toggle LEDs & buzzer at blinkInterval
    if (now - lastBlinkTime >= blinkInterval) {
        lastBlinkTime = now;
        ledState = !ledState;
        for (int i = 0; i < 6; i++) {
            digitalWrite(greenLEDPins[i], ledState && (i < numGreenOn));
            digitalWrite(redLEDPins[i],   ledState && (i < numRedOn));
        }
        digitalWrite(buzzerPin, ledState);
    }
}
