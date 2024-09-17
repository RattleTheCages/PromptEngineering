/*
001<Freestyle>Add a description, at the top, of what this code does.

This code reads the values from three potentiometers and uses those values to control the brightness of three LEDs and the angles of three servos.
The LED brightness and servo angle are updated every 22 milliseconds based on the potentiometer readings.
Additionally, the potentiometer values are printed to the Serial Monitor for debugging and monitoring purposes.
*/

#include <Servo.h>

// Pins for the potentiometers
const int potPin1 = A3;
const int potPin2 = A4;
const int potPin3 = A5;

// Pins for the LEDs
const int ledPin1 = 3;
const int ledPin2 = 5;
const int ledPin3 = 6;

// Pins for the Servos
const int servoPin1 = 9;
const int servoPin2 = 10;
const int servoPin3 = 11;

// Servo objects
Servo servo1;
Servo servo2;
Servo servo3;

void setup() {
  Serial.begin(9600);
  
  // Initialize LED pins as outputs
  pinMode(ledPin1, OUTPUT);
  pinMode(ledPin2, OUTPUT);
  pinMode(ledPin3, OUTPUT);
  
  // Attach the servos to their respective pins
  servo1.attach(servoPin1);
  servo2.attach(servoPin2);
  servo3.attach(servoPin3);
}

unsigned long previousMillis = 0;
const long interval = 22;

void loop() {
  unsigned long currentMillis = millis();
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    // Read potentiometer values
    int potValue1 = analogRead(potPin1);
    int potValue2 = analogRead(potPin2);
    int potValue3 = analogRead(potPin3);

    // Map the potentiometer values (0-1023) to PWM values (0-255)
    int ledBrightness1 = map(potValue1, 0, 1023, 0, 255);
    int ledBrightness2 = map(potValue2, 0, 1023, 0, 255);
    int ledBrightness3 = map(potValue3, 0, 1023, 0, 255);

    // Write the mapped values to the LEDs
    analogWrite(ledPin1, ledBrightness1);
    analogWrite(ledPin2, ledBrightness2);
    analogWrite(ledPin3, ledBrightness3);

    // Map the potentiometer values (0-1023) to servo angles (0-180 degrees)
    int servoAngle1 = map(potValue1, 0, 1023, 0, 180);
    int servoAngle2 = map(potValue2, 0, 1023, 0, 180);
    int servoAngle3 = map(potValue3, 0, 1023, 0, 180);

    // Write the mapped angles to the servos
    servo1.write(servoAngle1);
    servo2.write(servoAngle2);
    servo3.write(servoAngle3);

    // Print the potentiometer values to the Serial Monitor
    Serial.print("Pot1: ");
    Serial.print(potValue1);
    Serial.print(" - Pot2: ");
    Serial.print(potValue2);
    Serial.print(" - Pot3: ");
    Serial.print(potValue3);
    Serial.print("\n");
  }
}

/*
./arduino-cli compile --fqbn arduino:avr:mega recordServos
*/


