#include <algorithm>
#include <string>
#include "ESP32Servo.h"

// Servo settings
int delta = 15;               // How much to push back on correct answer

void playerMove(Servo playerServo, int playerPos, String command) {
    if (command == "MOVE_PLAYER_A") {
        playerPos = max(playerPos - delta, 0);
        playerServo.write(playerPos);
        Serial.println("Player A pushes!");
        Serial.print("New position: ");
        Serial.println(playerPos);
        client.println("OK");
    } else if (command == "MOVE_PLAYER_B") {
        playerPos = min(playerPos + delta, 180);
        playerServo.write(playerPos);
        Serial.println("Player B pushes!");
        Serial.print("New position: ");
        Serial.println(playerPos);
        client.println("OK");
    } else if (command == "RESET") {
        playerPos = 90;
        playerServo.write(playerPos);
        Serial.println("Reset!");
        client.println("OK");
    }
}