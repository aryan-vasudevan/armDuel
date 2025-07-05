#include <WiFi.h>

// const char* ssid = "Network name";
// const char* password = "Network password";

WiFiServer server(12345);

void setup() {

    Serial.begin(115200);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    
    Serial.println();
    Serial.print("Connected to WiFi\nIP: ");
    Serial.println(WiFi.localIP());

    server.begin();
    Serial.println("Server started on port 12345");
}

void loop() {
    // Accept commands from python prgm
    WiFiClient client = server.accept();

    if (client) {
        Serial.println("Client connected");

        while (client.connected()) {
            // Receive command
            if (client.available()) {
                String command = client.readStringUntil('\n');
                command.trim();
                Serial.print("Received: ");
                Serial.println(command);
            
                // Control if move player was invoked
                if (command == "MOVE_PLAYER") {
                    Serial.println("Command recognized, sending OK...");
                    client.println("OK");

                    // Send immediately
                    client.flush();
                }
            }
            
            // Breathing Room
            delay(10);
        }

    client.stop();
    Serial.println("Client disconnected");
    }
}
