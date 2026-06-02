#include <WiFi.h>
#include <WebServer.h>
#include <ESP32Servo.h>

const char* ssid = "RobotArm";
const char* password = "12345678";

WebServer server(80);

Servo baseServo;
Servo elbowServo;
Servo wristServo;
Servo clawServo;

bool autoMode = true;

// Target Positions
int tBase = 55;
int tElbow = 26;
int tWrist = 75;
int tClaw = 30;

// Current Positions
float cBase = 55;
float cElbow = 26;
float cWrist = 75;
float cClaw = 30;

String webpage = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{
background:#0f172a;
font-family:Arial;
margin:0;
padding:20px;
color:white;
}
.container{
background:#1e293b;
padding:20px;
border-radius:20px;
max-width:500px;
margin:auto;
box-shadow:0 0 30px rgba(0,255,255,.2);
}
h1{
text-align:center;
color:#38bdf8;
}
label{
display:block;
margin-top:15px;
}
input[type=range]{
width:100%;
}
button{
width:100%;
padding:15px;
font-size:18px;
border:none;
border-radius:12px;
background:#38bdf8;
margin-bottom:20px;
font-weight:bold;
}
.mode{
text-align:center;
font-size:20px;
margin-bottom:15px;
}
</style>
</head>

<body>

<div class="container">

<h1>🤖 Robot Arm</h1>

<div class="mode" id="mode">
AUTO MODE
</div>

<button onclick="toggleMode()">
Switch Mode
</button>

<label>Base (0-110)</label>
<input type="range" min="0" max="110" value="55" id="base">

<label>Elbow (0-53)</label>
<input type="range" min="0" max="53" value="26" id="elbow">

<label>Wrist (27-123)</label>
<input type="range" min="27" max="123" value="75" id="wrist">

<label>Claw (5-59)</label>
<input type="range" min="5" max="59" value="30" id="claw">

</div>

<script>

let autoMode = true;

function toggleMode()
{
    autoMode = !autoMode;

    document.getElementById("mode").innerHTML =
    autoMode ? "AUTO MODE" : "MANUAL MODE";

    fetch("/mode?value=" + (autoMode ? 1 : 0));
}

setInterval(() =>
{
    if(autoMode) return;

    fetch(`/control?base=${base.value}&elbow=${elbow.value}&wrist=${wrist.value}&claw=${claw.value}`);

},100);

</script>

</body>
</html>
)rawliteral";

void smoothServo()
{
    float speed = 0.12;

    cBase += (tBase - cBase) * speed;
    cElbow += (tElbow - cElbow) * speed;
    cWrist += (tWrist - cWrist) * speed;
    cClaw += (tClaw - cClaw) * speed;

    baseServo.write((int)cBase);
    elbowServo.write((int)cElbow);
    wristServo.write((int)cWrist);
    clawServo.write((int)cClaw);
}

void handleRoot()
{
    server.send(200,"text/html",webpage);
}

void handleMode()
{
    autoMode = server.arg("value").toInt();
    server.send(200,"text/plain","OK");
}

void handleControl()
{
    if(!autoMode)
    {
        tBase  = constrain(server.arg("base").toInt(),0,110);
        tElbow = constrain(server.arg("elbow").toInt(),0,53);
        tWrist = constrain(server.arg("wrist").toInt(),27,123);
        tClaw  = constrain(server.arg("claw").toInt(),5,59);
    }

    server.send(200,"text/plain","OK");
}

void readSerial()
{
    if(!autoMode) return;

    if(Serial.available())
    {
        String data = Serial.readStringUntil('\n');

        int b,e,w,c;

        if(sscanf(
            data.c_str(),
            "B%d,E%d,W%d,C%d",
            &b,&e,&w,&c) == 4)
        {
            tBase  = constrain(b,0,110);
            tElbow = constrain(e,0,53);
            tWrist = constrain(w,27,123);
            tClaw  = constrain(c,5,59);

            Serial.print("RX: ");
            Serial.println(data);
        }
    }
}

void setup()
{
    Serial.begin(115200);

    baseServo.attach(12);
    elbowServo.attach(14);
    wristServo.attach(27);
    clawServo.attach(13);

    baseServo.write(55);
    elbowServo.write(26);
    wristServo.write(75);
    clawServo.write(30);

    delay(1000);

    WiFi.softAP(ssid,password);

    Serial.println();
    Serial.println("WiFi Started");
    Serial.print("IP Address: ");
    Serial.println(WiFi.softAPIP());

    server.on("/", handleRoot);
    server.on("/mode", handleMode);
    server.on("/control", handleControl);

    server.begin();
}

void loop()
{
    server.handleClient();

    readSerial();

    smoothServo();

    delay(15);
}