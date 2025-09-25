/**************************************************************************/
/*! 
BASED ON:
    @file     trianglewave.pde
    @author   Adafruit Industries
    @license  BSD (see license.txt)

    This example will generate a triangle wave with the MCP4725 DAC.   

    This is an example sketch for the Adafruit MCP4725 breakout board
    ----> http://www.adafruit.com/products/935
 
    Adafruit invests time and resources providing this open source code, 
    please support Adafruit and open-source hardware by purchasing 
    products from Adafruit!
*/
/**************************************************************************/
#include <Wire.h>
#include <Adafruit_MCP4725.h>

Adafruit_MCP4725 dac;

int twelvebitvoltage = 0;

void setup(void) {
  Serial.begin(115200);
  //Serial.println("Hello!");

  // For Adafruit MCP4725A1 the address is 0x62 (default) or 0x63 (ADDR pin tied to VCC)
  // For MCP4725A0 the address is 0x60 or 0x61
  // For MCP4725A2 the address is 0x64 or 0x65
  dac.begin(0x62);
    
  //Serial.println("Setting voltage");
  //twelvebitvoltage = 4095;
  twelvebitvoltage = 0; // set to 0V at start-up
  dac.setVoltage(twelvebitvoltage, false);
}



// in this loop: add variable that can be defined during setup
  // this variable (0-4095) determines the voltage
  // ideally this variable is defined in the Mother Python script using serial input
/*
void loop(void) {
  dac.setVoltage(twelvebitvoltage, false);

}
*/
void loop() {
  while (!Serial.available()); // 
  twelvebitvoltage = Serial.readStringUntil('\n').toInt(); // read string data received through COM port
  // digitalWrite(led,i); // set LED to 1 (on) or 0 (off) according to the received string data
  dac.setVoltage(twelvebitvoltage, false);
}


// void loop(void) {
//     if(Serial.available() > 0){
//     twelvebitvoltage = Serial.read() - '0'; // need to use a function that reads multiple characters!
//     dac.setVoltage(twelvebitvoltage, false);
//     Serial.println(twelvebitvoltage);
//   //  if(i == 1){
//   //   digitalWrite(led, HIGH);
//   //   Serial.println(i);
//   //  } 
//   //   else if(i == 0){
//   //   digitalWrite(led, LOW);
//   //   Serial.println(i);
//   //   // add log of timestamp
//   //  } 
//   }
// }

// void loop(void) {
//     uint32_t counter;
//     // Run through the full 12-bit scale for a triangle wave
//     for (counter = 0; counter < 4095; counter++)
//     {
//       dac.setVoltage(counter, false);
//     }
//     for (counter = 4095; counter > 0; counter--)
//     {
//       dac.setVoltage(counter, false);
//     }
// }