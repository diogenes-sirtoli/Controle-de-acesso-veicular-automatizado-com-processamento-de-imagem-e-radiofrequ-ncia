#include "AESLib.h"
#include  <SPI.h>
#include "nRF24L01.h"
#include "RF24.h"

AESLib aesLib;
RF24 radio(12, 14, 26, 25, 27);

const byte address[6] = "00001";

String plaintext = "HELLO WORLD!";


char textoLimpo[256] = "ILU6995";
char ciphertext[512];

// AES Encryption Key
byte aes_key[] = { 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x00 };

// General initialization vector (you must use your own IV's in production for full security!!!)
byte aes_iv[N_BLOCK] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };

// Generate IV (once)
void aes_init() {
  //Serial.println("gen_iv()");
  aesLib.gen_iv(aes_iv);
 // Serial.println("encrypt()");
 // Serial.println(encrypt(strdup(plaintext.c_str()), plaintext.length(), aes_iv));
}

String encrypt(char * msg, uint16_t msgLen, byte iv[]) {
  int cipherlength = aesLib.get_cipher64_length(msgLen);
  char encrypted[cipherlength]; // AHA! needs to be large, 2x is not enough
  aesLib.encrypt64(msg, msgLen, encrypted, aes_key, sizeof(aes_key), iv);
 // Serial.print("encrypted = "); Serial.println(encrypted);
  return String(encrypted);
}

void setup() {
  Serial.begin(9600);

  // ----- RADIO FREQUÊNCIA - MODO TRANSMISSOR -----
  radio.begin();
  radio.openWritingPipe(address);
  radio.setChannel(90);
  radio.setPALevel(RF24_PA_MIN);
  radio.stopListening();

 // -----------

 aes_init();
 aesLib.set_paddingmode(paddingMode::CMS);

}

unsigned long loopcount = 0;
byte enc_iv[N_BLOCK] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }; // iv_block gets written to, provide own fresh copy...
byte dec_iv[N_BLOCK] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };


void loop() {

    // CRIPTOGRAFA
   // Serial.println(textoLimpo);
    uint16_t clen = String(textoLimpo).length();
    String encrypted = encrypt(textoLimpo, clen, enc_iv);
    sprintf(ciphertext, "%s", encrypted.c_str());
   // Serial.print("Ciphertext: ");
   // Serial.println(encrypted);
    delay(100);

  
    for (int i = 0; i < 16; i++) {
      enc_iv[i] = 0;
       dec_iv[i] = 0;
    }
    
      // ENVIA MENSAGEM POR RADIO
    int criptografadaChar_len = encrypted.length()+1;
    char criptografadaChar_array[criptografadaChar_len];
    encrypted.toCharArray(criptografadaChar_array, criptografadaChar_len);
    Serial.print("Mensagem original: ");
    Serial.println(textoLimpo);
    Serial.print("Mensagem enviada por rádio: ");
    Serial.println(criptografadaChar_array);   
    radio.write(criptografadaChar_array, sizeof(criptografadaChar_array));
    delay(100);
  
}
