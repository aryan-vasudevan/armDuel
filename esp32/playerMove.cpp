#include <algorithm>
#include "ESP32Servo.h"

// Servo settings
int stepBack = 20;               // How much to push back on correct answer

void playerMove(Servo playerServo, int playerPos) {
    playerPos = max(playerPos - stepBack, 0);
    playerServo.write(playerPos);
    Serial.println("Player pushed back!");
    Serial.print("New position: ");
    Serial.println(playerPos);
    client.println("OK");
}