//#include  <SPI.h>
//#include "nRF24L01.h"
#include "RF24.h"
#include "AESLib.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <Arduino_JSON.h>
//#include <ArduinoJson.h>
AESLib aesLib;

#define LED_VERDE 13
#define LED_VERMELHO 32
#define LED_AMARELO 33

const char* ssid       = "Teste";
const char* password   = "Tudobem03";

HTTPClient http;
String resultadoAPI;
JSONVar myArray;
JSONVar keys;
String resultadoApiString;
String decriptografado;
int placaJaEsta = 0;
bool portaoAberto = false;

long tempoAnterior = 0;
long tempoVerificaPortao = 1000;
int contTempoPortaoAberto = 0;

long unsigned int tempoPermissao[50];
long unsigned int tempoResultante;
int contPlacasPerto = 0;
String placasPerto[50][2];  //coluna 1 = placa    coluna 2 = permitido ou não (0 ou 1)
String abrirPortao = "";

RF24 radio(12, 14, 26, 25, 27);

const byte address[6] = "00001";
char text[33] = "";
int contTempo = 0;

// -----  DESCRIPTOGRAFIA ----
String plaintext = "HELLO WORLD!";
char textoLimpo[256];
char ciphertext[512];

// AES Encryption Key
byte aes_key[] = { 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x00 };

// General initialization vector (you must use your own IV's in production for full security!!!)
byte aes_iv[N_BLOCK] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };

// Generate IV (once)
void aes_init() {
  Serial.println("gen_iv()");
  aesLib.gen_iv(aes_iv);
  Serial.println("encrypt()");
  Serial.println(encrypt(strdup(plaintext.c_str()), plaintext.length(), aes_iv));
}

String encrypt(char * msg, uint16_t msgLen, byte iv[]) {
  int cipherlength = aesLib.get_cipher64_length(msgLen);
  char encrypted[cipherlength]; // AHA! needs to be large, 2x is not enough
  aesLib.encrypt64(msg, msgLen, encrypted, aes_key, sizeof(aes_key), iv);
  Serial.print("encrypted = "); Serial.println(encrypted);
  return String(encrypted);
}

String decrypt(char * msg, uint16_t msgLen, byte iv[]) {
  char decrypted[msgLen];
  aesLib.decrypt64(msg, msgLen, decrypted, aes_key, sizeof(aes_key), iv);
  return String(decrypted);
}

//-------------------------------------------------------------

void ligaLampVermelha(){
  digitalWrite(LED_VERMELHO, LOW); // liga apenas luz VERMELHA
  digitalWrite(LED_AMARELO, HIGH);
  digitalWrite(LED_VERDE, HIGH);
}
void ligaLampVerde(){
  digitalWrite(LED_VERMELHO, HIGH); // liga apenas luz VERMELHA
  digitalWrite(LED_AMARELO, HIGH);
  digitalWrite(LED_VERDE, LOW);
}
void ligaLampAmarela_Vermelha(){
  digitalWrite(LED_VERMELHO, LOW); // liga apenas luz VERMELHA
  digitalWrite(LED_AMARELO, LOW);
  digitalWrite(LED_VERDE, HIGH);
}

//------------ CONSULTA A PLACA NA API -------------------

String consultaPlacaAPI(String placa){
  http.begin("http://177.44.248.99:5000/consultaPlacaRF/"+placa); //Specify the URL
    int httpCode = http.GET();
    if (httpCode > 0) { //Check for the returning code
        resultadoAPI = http.getString();
        myArray = JSON.parse(resultadoAPI);
      //  Serial.println(myArray);
        keys = myArray.keys();
      //  Serial.println(myArray[keys[0]]);
        resultadoApiString = JSON.stringify(myArray[keys[0]]); //Pega o valor do atributo da JSON e transforma pra STRING para usar no código
        return resultadoApiString;
      }else{
        return "9";
      }
      
}
// ----------------------------------------------------------------

//------------ CONSULTA NA API SE PODE ABRIR PORTÃO -------------------

String podeAbrirPortaoAPI(){
  http.begin("http://177.44.248.99:5000/abrirPortao/"); //Specify the URL
    int httpCode = http.GET();
    if (httpCode > 0) { //Check for the returning code
        resultadoAPI = http.getString();
        myArray = JSON.parse(resultadoAPI);
      //  Serial.println(myArray);
        keys = myArray.keys();
      //  Serial.println(myArray[keys[0]]);
        resultadoApiString = JSON.stringify(myArray[keys[0]]); //Pega o valor do atributo da JSON e transforma pra STRING para usar no código
        return resultadoApiString;
      }else{
        return "9";
      }
      
}
// ----------------------------------------------------------------

//------------ REMOVE PLACA RF API -------------------------------

void removePlacaAPI(String placa){
  http.begin("http://177.44.248.99:5000/removePlacaRF/"+placa); //Specify the URL
  int httpCode = http.GET();
}
// ----------------------------------------------------------------

void setup() {
  Serial.begin(9600);

  //Lâmpadas da sinaleira
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_AMARELO, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);

 //----------- Conecta WIFI --------------
  Serial.printf("Connecting to %s ", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
  }
  Serial.println(" CONNECTED");

  //------------ RECEPTOR DE RÁDIO -----------
  
  radio.begin();
  radio.openReadingPipe(0, address);
  radio.setChannel(90);
  radio.setPALevel(RF24_PA_MIN);
  radio.startListening();
// ---------------------------------------------
  
  aes_init();
  aesLib.set_paddingmode(paddingMode::CMS);
}

byte enc_iv[N_BLOCK] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 }; // iv_block gets written to, provide own fresh copy...
byte dec_iv[N_BLOCK] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0 };



void loop() {
    if(WiFi.status() != WL_CONNECTED) {  //Se desconectar do WIFI, vai ficar tentando reconectar até conectar
      WiFi.begin(ssid, password);
      while (WiFi.status() != WL_CONNECTED) {
          delay(500);
          Serial.print(".");
      }
    }
    if (radio.available()) {
      radio.read(&text, sizeof(text));
      Serial.print("Leitura da rádio: ");
      Serial.println(text);
      uint16_t dlen = sizeof(text);
      decriptografado = decrypt(text, dlen, dec_iv);
      Serial.print("Texto descriptografado: ");
      Serial.println(decriptografado);
      for (int i = 0; i < 16; i++) {
        enc_iv[i] = 0;
        dec_iv[i] = 0;
      }
      for(int cont = 0; cont < contPlacasPerto; cont++){
        if(decriptografado == placasPerto[cont][0]){
          placaJaEsta = 1; // 1 = sim 0 = não
        }
      }
      if(placaJaEsta == 0){
        String resultado = consultaPlacaAPI(decriptografado);   //RESULTADO = 0: NEGADO
        //Serial.println(resultado);                              //RESULTADO = 1: PERMITIDO
        if(resultado == "1"){
         tempoPermissao[contPlacasPerto] = millis();  //insere o tempo que a placa do veículo foi adicionada
         placasPerto[contPlacasPerto][0] = decriptografado;
         Serial.print("--------------------------  A seguinte placa foi inserida na matriz: ");
         Serial.println(decriptografado);
         placasPerto[contPlacasPerto][1] = "1";
         contPlacasPerto++;
        }
      }
      placaJaEsta = 0;
    }
    if(contPlacasPerto > 0){ //se tiver alguma placa por perto
        if(portaoAberto == false){
            ligaLampAmarela_Vermelha();
            if(portaoAberto == false){
              if(millis()>= tempoAnterior+tempoVerificaPortao){ //verifica a cada segundo
                tempoAnterior = millis();
                abrirPortao = podeAbrirPortaoAPI(); //verifica na API se é para abrir o portão ou não
              }
            }
        }
        for(int cont = 0; cont < contPlacasPerto; cont++){
            tempoResultante = (millis()- tempoPermissao[cont]);
            if(tempoResultante >= 180000){
                Serial.print("-------------------------- O tempo dessa placa se foi:");
                Serial.println(cont);
                for(int cont2 = cont; cont2 < contPlacasPerto; cont2++){
                      removePlacaAPI(placasPerto[cont2][0]); //remove placa na API também
                      placasPerto[cont2][0] = placasPerto[cont2+1][0];
                      placasPerto[cont2][1] = placasPerto[cont2+1][1];
                      tempoPermissao[cont2] = tempoPermissao[cont2+1];
                    }
               contPlacasPerto--;
           //   Serial.println(contPlacasPerto);
            } 
        }      
     }
     if(abrirPortao == "1"){
         portaoAberto = true;
         ligaLampVerde();
         delay(10);
         contTempoPortaoAberto = contTempoPortaoAberto + 10;
         if(contTempoPortaoAberto>= 180000){ //tempo configurável para portão aberto
             portaoAberto = false;
             contTempoPortaoAberto = 0;
         } 
     }
     if((contPlacasPerto == 0)&& (portaoAberto == false)){
        ligaLampVermelha();
     }

}
