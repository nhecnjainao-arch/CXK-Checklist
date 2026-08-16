from flask import Flask, request, redirect, url_for, render_template_string, send_file, flash
import sqlite3
import os
import json
import base64
import uuid
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)

from PIL import Image as PILImage


# ============================================================
# CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = "CHANGE_THIS_SECRET_KEY"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"

DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

DB_FILE = DATA_DIR / "cxk_pm.sqlite3"


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            terminal_id TEXT,
            work_order TEXT,
            visit_date TEXT,
            engineer TEXT,
            custodian TEXT,
            created_at TEXT,
            pdf_file TEXT,
            json_data TEXT
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ============================================================
# CHECKLIST
# ============================================================

CHECKLIST = [

    {
        "section": "SEGMA",
        "items": [

            ("1",
             "Was the machine online with successful transactions at the time of visit?"),

            ("2",
             "Check card hopper levels - Take clear photo showing the top of the card."),

            ("3",
             "Check supplies status from LCD - Take photos."),

            ("4a",
             "Preventive maintenance - Run cleaning card and clean the sensors."),

            ("4b",
             "Preventive maintenance - Check cleaning sleeve for ideal stickiness and change if necessary."),

            ("5",
             "Empty the reject bin."),

            ("6",
             "Empty output hopper bin."),

            ("7",
             "Clear Card Jams using the manual advance knob."),

            ("8",
             "Replenish card hoppers using stock from custodian if level is low."),

            ("9",
             "Call SNB ATM coordinators if custodian is unable to provide replenishment."),

            ("10",
             "Ensure cards are correctly loaded in respective hoppers as per bank configuration."),

            ("11",
             "Ensure cards are loaded with correct orientation."),

            ("12",
             "Shuffle cards in the hopper to ensure no static."),

            ("13",
             "Ensure hoppers are not overloaded."),

            ("14",
             "Replace consumables if LCD displays low levels (20% or below)."),

            ("15",
             "Clear all errors from LCD Panel of printer."),

            ("16",
             "Inspect surroundings of SIGMA - Dust / AC / Sunlight etc.")
        ]
    },

    {
        "section": "HP & STATEMENT PRINTER",
        "items": [

            ("1",
             "Was the machine online with successful transactions at the time of visit?"),

            ("2",
             "Check TRAYS 2 & 3 loaded enough with A4 paper with suggested GSM."),

            ("3",
             "Check Toner & paper supplies notification from LCD."),

            ("4a",
             "Preventive maintenance - Clean stamper F1-F6 sensors."),

            ("4b",
             "Preventive maintenance - Clean/recondition stamper transport belts and paper guide."),

            ("4c",
             "Preventive maintenance - Clean stamp plate/rubber."),

            ("4d",
             "Preventive maintenance - Replace ink roller and align properly."),

            ("4e",
             "Preventive maintenance - Replace HP toner if required."),

            ("4f",
             "Preventive maintenance - Replenish new good paper on TRAYS 2 & 3."),

            ("4g",
             "Ensure HP and STAMPER modules are free from debris or dust."),

            ("4h",
             "Ensure no misalignment between HP and STAMPER modules."),

            ("5",
             "Empty reject/retract bin."),

            ("6",
             "Empty collection bin."),

            ("7",
             "Offline continuous test with 20 pages successfully."),

            ("8",
             "Transaction test for IBAN print successfully."),

            ("9",
             "Transaction test for STATEMENT print successfully."),

            ("10a",
             "Call SNB ATM coordinators if custodian is unable to provide replenishment."),

            ("10b",
             "Call SNB ATM coordinators if custodian is unable to support transaction test."),

            ("16",
             "Inspect surroundings of CXK - Dust / AC / Sunlight etc.")
        ]
    }
]


# ============================================================
# HTML
# ============================================================

HTML = r"""
<!DOCTYPE html>
<html>

<head>

<meta charset="UTF-8">

<meta name="viewport"
content="width=device-width, initial-scale=1">

<title>CXK PM Checklist System</title>

<style>

* {
    box-sizing:border-box;
}

body {
    margin:0;
    font-family:Arial,Helvetica,sans-serif;
    background:#f3f6f9;
    color:#202b36;
}

header {
    background:#0c4f82;
    color:white;
    padding:16px 5%;
    display:flex;
    justify-content:space-between;
    align-items:center;
    position:sticky;
    top:0;
    z-index:100;
}

.logo {
    font-weight:bold;
    font-size:20px;
}

nav a {
    color:white;
    text-decoration:none;
    margin-left:20px;
}

.container {
    max-width:1200px;
    margin:25px auto;
    padding:0 15px;
}

.card {
    background:white;
    border-radius:12px;
    padding:20px;
    margin-bottom:20px;
    box-shadow:0 2px 10px rgba(0,0,0,.07);
}

h1 {
    color:#0c4f82;
}

h2 {
    color:#0c4f82;
    border-bottom:2px solid #e5edf4;
    padding-bottom:8px;
}

.form-grid {
    display:grid;
    grid-template-columns:repeat(3,1fr);
    gap:15px;
}

label {
    font-weight:bold;
    font-size:14px;
}

input,
select,
textarea {
    width:100%;
    padding:10px;
    margin-top:5px;
    border:1px solid #cbd5df;
    border-radius:7px;
    font-size:14px;
}

textarea {
    min-height:80px;
}

.item {
    border:1px solid #dce4eb;
    border-radius:10px;
    padding:15px;
    margin:12px 0;
}

.item-title {
    display:flex;
    gap:12px;
    align-items:flex-start;
}

.number {
    background:#0c4f82;
    color:white;
    width:34px;
    height:34px;
    border-radius:50%;
    display:flex;
    justify-content:center;
    align-items:center;
    flex-shrink:0;
    font-weight:bold;
}

.response {
    display:flex;
    gap:25px;
    margin:15px 0;
}

.response label {
    display:flex;
    align-items:center;
    gap:5px;
}

.response input {
    width:auto;
}

.photo {
    background:#edf6ff;
    padding:10px;
    display:inline-block;
    border-radius:7px;
    cursor:pointer;
}

.signature-area {
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:25px;
}

.signature {
    width:100%;
    height:200px;
    border:2px dashed #8797a7;
    background:white;
    border-radius:8px;
    touch-action:none;
}

button,
.btn {
    border:none;
    background:#e4ebf2;
    padding:12px 18px;
    border-radius:7px;
    cursor:pointer;
    text-decoration:none;
    color:#17212b;
    font-weight:bold;
}

.primary {
    background:#0c4f82;
    color:white;
}

.submit {
    font-size:18px;
    padding:16px 25px;
}

.actions {
    display:flex;
    gap:10px;
    flex-wrap:wrap;
    margin:20px 0;
}

table {
    width:100%;
    border-collapse:collapse;
}

th,
td {
    border:1px solid #d5dde5;
    padding:9px;
    text-align:left;
}

th {
    background:#eaf1f7;
}

.alert {
    padding:12px;
    background:#ffe2e2;
    color:#991b1b;
    border-radius:8px;
    margin-bottom:15px;
}

@media(max-width:800px) {

    .form-grid {
        grid-template-columns:1fr 1fr;
    }

    .signature-area {
        grid-template-columns:1fr;
    }

}

@media(max-width:550px) {

    header {
        flex-direction:column;
        gap:10px;
    }

    nav a {
        margin:0 7px;
    }

    .form-grid {
        grid-template-columns:1fr;
    }

    .response {
        flex-direction:column;
        gap:8px;
    }

}

</style>

</head>


<body>

<header>

<div class="logo">
CXK PM CHECKLIST
</div>

<nav>

<a href="/">Dashboard</a>

<a href="/new">New Checklist</a>

<a href="/history">History</a>

</nav>

</header>


<div class="container">

{% with messages = get_flashed_messages() %}

{% if messages %}

<div class="alert">

{{ messages[0] }}

</div>

{% endif %}

{% endwith %}


{% block content %}

{% endblock %}

</div>

</body>

</html>
"""


# ============================================================
# DASHBOARD
# ============================================================

HOME_HTML = HTML.replace(
"{% block content %}{% endblock %}",
r"""

<div class="card">

<h1>
SNB ASK 1000 SIGMA / CXK
</h1>

<p>
Automated FLM Preventive Maintenance Checklist
</p>

<div class="actions">

<a class="btn primary"
href="/new">

➕ Start New Checklist

</a>

<a class="btn"
href="/history">

📋 Completed Reports

</a>

</div>

</div>


<div class="card">

<h2>System Functions</h2>

<ul>

<li>Digital PM checklist</li>

<li>Engineer information</li>

<li>Customer / custodian information</li>

<li>Yes / No / N/A inspection results</li>

<li>Observation and close-out notes</li>

<li>Photo capture using mobile camera</li>

<li>Engineer signature</li>

<li>Customer signature</li>

<li>Automatic PDF generation</li>

<li>Completed report history</li>

</ul>

</div>

"""
)


# ============================================================
# FORM
# ============================================================

FORM_HTML = HTML.replace(
"{% block content %}{% endblock %}",
r"""

<form
method="POST"
action="/submit"
enctype="multipart/form-data"
id="checklistForm">


<div class="card">

<h1>New PM Checklist</h1>

<div class="form-grid">

<label>
Terminal ID *
<input name="terminal_id" required>
</label>

<label>
Date of Visit
<input type="date" name="visit_date">
</label>

<label>
Work Order
<input name="work_order">
</label>

<label>
Arrival Time
<input type="time" name="arrival_time">
</label>

<label>
Departure Time
<input type="time" name="departure_time">
</label>

<label>
Activity Start
<input type="time" name="activity_start">
</label>

<label>
Activity Finish
<input type="time" name="activity_finish">
</label>

<label>
Cabinet Type
<input name="cabinet_type" value="CXK">
</label>

<label>
Variant Type
<input name="variant_type" value="FRONT">
</label>

<label>
Engineer Name
<input name="engineer">
</label>

<label>
Engineer Mobile
<input name="engineer_mobile">
</label>

<label>
Customer / Custodian
<input name="custodian">
</label>

<label>
Customer Mobile
<input name="custodian_mobile">
</label>

</div>

</div>


{% for section in checklist %}

<div class="card">

<h2>{{ section.section }}</h2>


{% for no,text in section.items %}

<div class="item">

<div class="item-title">

<div class="number">

{{ no }}

</div>

<div>

<strong>
{{ text }}
</strong>

</div>

</div>


<div class="response">

<label>

<input
type="radio"
name="response_{{ section.section|replace(' ','_') }}_{{ loop.index }}"
value="YES"
required>

YES

</label>


<label>

<input
type="radio"
name="response_{{ section.section|replace(' ','_') }}_{{ loop.index }}"
value="NO">

NO

</label>


<label>

<input
type="radio"
name="response_{{ section.section|replace(' ','_') }}_{{ loop.index }}"
value="N/A">

N/A

</label>

</div>


<textarea
name="observation_{{ section.section|replace(' ','_') }}_{{ loop.index }}"
placeholder="Observation / remarks">
</textarea>


<label class="photo">

📷 Take / Attach Photo

<input
type="file"
name="photo_{{ section.section|replace(' ','_') }}_{{ loop.index }}"
accept="image/*"
capture="environment"
multiple>

</label>


</div>

{% endfor %}

</div>

{% endfor %}


<div class="card">

<h2>
Final Observations / Close-Out
</h2>

<textarea
name="final_observation"
rows="6"
placeholder="Enter final findings, actions completed, machine status, transaction test results and pending items">
</textarea>

</div>


<div class="card">

<h2>
Signatures
</h2>


<div class="signature-area">


<div>

<h3>
Customer / Custodian Signature
</h3>

<canvas
id="customerCanvas"
class="signature">
</canvas>

<br><br>

<button
type="button"
onclick="clearSignature('customerCanvas')">

Clear

</button>

<input
type="hidden"
name="customer_signature"
id="customer_signature">

</div>


<div>

<h3>
Engineer Signature
</h3>

<canvas
id="engineerCanvas"
class="signature">
</canvas>

<br><br>

<button
type="button"
onclick="clearSignature('engineerCanvas')">

Clear

</button>

<input
type="hidden"
name="engineer_signature"
id="engineer_signature">

</div>


</div>

<p>
You can sign using the mouse, finger or stylus.
</p>

</div>


<div class="card">

<button
type="submit"
class="btn primary submit">

✅ COMPLETE CHECKLIST & GENERATE PDF

</button>

</div>


</form>


<script>

function setupSignature(canvasId, hiddenId)
{

const canvas =
document.getElementById(canvasId);

const hidden =
document.getElementById(hiddenId);

const ctx =
canvas.getContext("2d");

let drawing = false;


function resize()
{

const rect =
canvas.getBoundingClientRect();

const ratio =
window.devicePixelRatio || 1;

canvas.width =
rect.width * ratio;

canvas.height =
rect.height * ratio;

ctx.scale(ratio,ratio);

ctx.lineWidth = 2;

ctx.lineCap = "round";

}


resize();


window.addEventListener(
"resize",
resize
);


function position(event)
{

const rect =
canvas.getBoundingClientRect();

let clientX;
let clientY;


if(event.touches)
{

clientX =
event.touches[0].clientX;

clientY =
event.touches[0].clientY;

}

else
{

clientX =
event.clientX;

clientY =
event.clientY;

}


return {

x:clientX-rect.left,

y:clientY-rect.top

};

}


function start(event)
{

event.preventDefault();

drawing=true;

const p =
position(event);

ctx.beginPath();

ctx.moveTo(
p.x,
p.y
);

}


function draw(event)
{

if(!drawing)
return;

event.preventDefault();

const p =
position(event);

ctx.lineTo(
p.x,
p.y
);

ctx.stroke();

}


function stop()
{

if(!drawing)
return;

drawing=false;

hidden.value =
canvas.toDataURL(
"image/png"
);

}


canvas.addEventListener(
"mousedown",
start
);

canvas.addEventListener(
"mousemove",
draw
);

canvas.addEventListener(
"mouseup",
stop
);

canvas.addEventListener(
"mouseleave",
stop
);


canvas.addEventListener(
"touchstart",
start,
{passive:false}
);

canvas.addEventListener(
"touchmove",
draw,
{passive:false}
);

canvas.addEventListener(
"touchend",
stop
);

}


function clearSignature(canvasId)
{

const canvas =
document.getElementById(canvasId);

const ctx =
canvas.getContext("2d");

ctx.clearRect(
0,
0,
canvas.width,
canvas.height
);

const hiddenId =
canvasId === "customerCanvas"
?
"customer_signature"
:
"engineer_signature";

document.getElementById(hiddenId).value="";

}


setupSignature(
"customerCanvas",
"customer_signature"
);


setupSignature(
"engineerCanvas",
"engineer_signature"
);


document
.getElementById("checklistForm")
.addEventListener(
"submit",
function(event)
{

const customer =
document.getElementById(
"customer_signature"
).value;

const engineer =
document.getElementById(
"engineer_signature"
).value;


if(!customer)
{

alert(
"Please capture the customer/custodian signature."
);

event.preventDefault();

return;

}


if(!engineer)
{

alert(
"Please capture the engineer signature."
);

event.preventDefault();

return;

}

});


</script>

"""
)


# ============================================================
# HISTORY
# ============================================================

HISTORY_HTML = HTML.replace(
"{% block content %}{% endblock %}",
r"""

<div class="card">

<h1>
Completed Reports
</h1>

<form method="GET">

<input
name="q"
placeholder="Search Terminal ID / Work Order / Engineer / Custodian"
value="{{ q }}"
>

<br><br>

<button class="btn primary">
Search
</button>

</form>

</div>


<div class="card">

<div style="overflow-x:auto">

<table>

<tr>

<th>ID</th>

<th>Date</th>

<th>Terminal</th>

<th>Work Order</th>

<th>Engineer</th>

<th>Customer</th>

<th>PDF</th>

</tr>


{% for r in reports %}

<tr>

<td>
{{ r["id"] }}
</td>

<td>
{{ r["visit_date"] }}
</td>

<td>
{{ r["terminal_id"] }}
</td>

<td>
{{ r["work_order"] }}
</td>

<td>
{{ r["engineer"] }}
</td>

<td>
{{ r["custodian"] }}
</td>

<td>

<a
class="btn"
target="_blank"
href="/pdf/{{ r['pdf_file'] }}">

Open PDF

</a>

</td>

</tr>

{% else %}

<tr>

<td colspan="7">

No reports found.

</td>

</tr>

{% endfor %}

</table>

</div>

</div>

"""
)


# ============================================================
# PDF GENERATOR
# ============================================================

def clean_filename(value):

    value = str(value or "NA")

    return "".join(
        c if c.isalnum() or c in "-_"
        else "_"
        for c in value
    )


def create_pdf(report):

    info = report["info"]

    filename = (
        "CXK_PM_"
        + clean_filename(info["terminal_id"])
        + "_"
        + clean_filename(info["work_order"])
        + "_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".pdf"
    )

    pdf_path = REPORT_DIR / filename


    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        fontSize=15,
        leading=18,
        alignment=TA_CENTER
    )

    small = ParagraphStyle(
        "small",
        parent=styles["BodyText"],
        fontSize=7,
        leading=8
    )

    normal = ParagraphStyle(
        "normal",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=10
    )


    document = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=12*mm,
        rightMargin=12*mm,
        topMargin=12*mm,
        bottomMargin=12*mm
    )


    story = []


    story.append(
        Paragraph(
            "SNB ASK 1000 SIGMA / CXK",
            title_style
        )
    )

    story.append(
        Paragraph(
            "FLM PREVENTIVE MAINTENANCE CHECKLIST",
            title_style
        )
    )

    story.append(
        Spacer(1,8)
    )


    info_rows = [

        [
            Paragraph("<b>Terminal ID</b>",small),
            info["terminal_id"],

            Paragraph("<b>Date</b>",small),
            info["visit_date"]
        ],

        [
            Paragraph("<b>Work Order</b>",small),
            info["work_order"],

            Paragraph("<b>Engineer</b>",small),
            info["engineer"]
        ],

        [
            Paragraph("<b>Customer/Custodian</b>",small),
            info["custodian"],

            Paragraph("<b>Cabinet</b>",small),
            info["cabinet_type"]
        ],

        [
            Paragraph("<b>Arrival</b>",small),
            info["arrival_time"],

            Paragraph("<b>Departure</b>",small),
            info["departure_time"]
        ]

    ]


    table = Table(
        info_rows,
        colWidths=[
            30*mm,
            60*mm,
            30*mm,
            60*mm
        ]
    )


    table.setStyle(
        TableStyle([
            (
                "GRID",
                (0,0),
                (-1,-1),
                .4,
                colors.grey
            ),

            (
                "BACKGROUND",
                (0,0),
                (0,-1),
                colors.HexColor("#edf2f7")
            ),

            (
                "BACKGROUND",
                (2,0),
                (2,-1),
                colors.HexColor("#edf2f7")
            ),

            (
                "VALIGN",
                (0,0),
                (-1,-1),
                "TOP"
            )
        ])
    )


    story.append(table)

    story.append(
        Spacer(1,10)
    )


    for section in CHECKLIST:

        story.append(
            Paragraph(
                section["section"],
                styles["Heading2"]
            )
        )


        rows = [

            [
                Paragraph("<b>No.</b>",small),

                Paragraph(
                    "<b>Inspection / Activity</b>",
                    small
                ),

                Paragraph(
                    "<b>Result</b>",
                    small
                ),

                Paragraph(
                    "<b>Observation</b>",
                    small
                )
            ]

        ]


        for index,(no,text) in enumerate(section["items"]):

            key = (
                section["section"]
                .replace(" ","_")
                + "_"
                + str(index+1)
            )

            item = report["items"].get(
                key,
                {}
            )


            response = item.get(
                "response",
                "-"
            )


            observation = item.get(
                "observation",
                ""
            )


            photos = item.get(
                "photos",
                []
            )


            if photos:

                observation += (
                    " "
                    + str(len(photos))
                    + " photo(s) attached."
                )


            rows.append(
                [
                    Paragraph(no,small),

                    Paragraph(
                        text,
                        small
                    ),

                    Paragraph(
                        response,
                        small
                    ),

                    Paragraph(
                        observation or "-",
                        small
                    )
                ]
            )


        checklist_table = Table(
            rows,
            colWidths=[
                10*mm,
                88*mm,
                23*mm,
                59*mm
            ],
            repeatRows=1
        )


        checklist_table.setStyle(
            TableStyle([

                (
                    "GRID",
                    (0,0),
                    (-1,-1),
                    .35,
                    colors.grey
                ),

                (
                    "BACKGROUND",
                    (0,0),
                    (-1,0),
                    colors.HexColor("#e8eef5")
                ),

                (
                    "VALIGN",
                    (0,0),
                    (-1,-1),
                    "TOP"
                )

            ])
        )


        story.append(
            checklist_table
        )

        story.append(
            Spacer(1,8)
        )


    story.append(
        Paragraph(
            "FINAL OBSERVATIONS / CLOSE-OUT",
            styles["Heading2"]
        )
    )


    story.append(
        Paragraph(
            info["final_observation"]
            or "No additional observations.",
            normal
        )
    )


    story.append(
        Spacer(1,15)
    )


    signature_rows = []


    for role,label in [

        (
            "customer",
            "CUSTOMER / CUSTODIAN SIGNATURE"
        ),

        (
            "engineer",
            "ENGINEER SIGNATURE"
        )

    ]:

        cell = [
            Paragraph(
                f"<b>{label}</b>",
                small
            )
        ]


        signature_file = report[
            "signatures"
        ].get(role)


        if signature_file:

            image_path = (
                UPLOAD_DIR
                / signature_file
            )


            if image_path.exists():

                try:

                    image = Image(
                        str(image_path),
                        width=70*mm,
                        height=25*mm
                    )

                    cell.append(image)

                except Exception:

                    pass


        signature_rows.append(cell)


    signature_table = Table(
        [signature_rows],
        colWidths=[
            88*mm,
            88*mm
        ]
    )


    signature_table.setStyle(
        TableStyle([

            (
                "BOX",
                (0,0),
                (-1,-1),
                .5,
                colors.grey
            ),

            (
                "INNERGRID",
                (0,0),
                (-1,-1),
                .5,
                colors.grey
            ),

            (
                "VALIGN",
                (0,0),
                (-1,-1),
                "TOP"
            )

        ])
    )


    story.append(
        signature_table
    )


    story.append(
        Spacer(1,10)
    )


    story.append(
        Paragraph(
            "Generated automatically by CXK PM Checklist System",
            small
        )
    )


    document.build(story)


    return filename


# ============================================================
# SAVE IMAGE
# ============================================================

def save_image(upload):

    if not upload:
        return None


    if not upload.filename:
        return None


    extension = (
        upload.filename
        .rsplit(".",1)[-1]
        .lower()
    )


    allowed = {
        "jpg",
        "jpeg",
        "png",
        "webp"
    }


    if extension not in allowed:
        return None


    filename = (
        uuid.uuid4().hex
        + "."
        + extension
    )


    destination = (
        UPLOAD_DIR
        / filename
    )


    upload.save(destination)


    try:

        image = PILImage.open(
            destination
        )

        image.thumbnail(
            (1800,1800)
        )


        if image.mode not in (
            "RGB",
            "RGBA"
        ):

            image = image.convert(
                "RGB"
            )


        image.save(
            destination,
            quality=85
        )

    except Exception:

        pass


    return filename


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():

    return render_template_string(
        HOME_HTML
    )


@app.route("/new")
def new_checklist():

    return render_template_string(
        FORM_HTML,
        checklist=CHECKLIST
    )


@app.route("/submit",methods=["POST"])
def submit():

    form = request.form


    terminal_id = (
        form.get(
            "terminal_id",
            ""
        ).strip()
    )


    if not terminal_id:

        flash(
            "Terminal ID is required."
        )

        return redirect(
            "/new"
        )


    report = {

        "info": {

            "terminal_id":
                terminal_id,

            "visit_date":
                form.get(
                    "visit_date",
                    ""
                ),

            "arrival_time":
                form.get(
                    "arrival_time",
                    ""
                ),

            "departure_time":
                form.get(
                    "departure_time",
                    ""
                ),

            "activity_start":
                form.get(
                    "activity_start",
                    ""
                ),

            "activity_finish":
                form.get(
                    "activity_finish",
                    ""
                ),

            "cabinet_type":
                form.get(
                    "cabinet_type",
                    ""
                ),

            "variant_type":
                form.get(
                    "variant_type",
                    ""
                ),

            "engineer":
                form.get(
                    "engineer",
                    ""
                ),

            "engineer_mobile":
                form.get(
                    "engineer_mobile",
                    ""
                ),

            "work_order":
                form.get(
                    "work_order",
                    ""
                ),

            "custodian":
                form.get(
                    "custodian",
                    ""
                ),

            "custodian_mobile":
                form.get(
                    "custodian_mobile",
                    ""
                ),

            "final_observation":
                form.get(
                    "final_observation",
                    ""
                )

        },

        "items": {},

        "signatures": {},

        "photos": []

    }


    # ========================================================
    # CHECKLIST DATA
    # ========================================================

    for section in CHECKLIST:

        section_key = (
            section["section"]
            .replace(" ","_")
        )


        for index,(no,text) in enumerate(
            section["items"]
        ):

            key = (
                section_key
                + "_"
                + str(index+1)
            )


            photos = []


            files = request.files.getlist(
                "photo_" + key
            )


            for upload in files:

                saved = save_image(
                    upload
                )

                if saved:

                    photos.append(
                        saved
                    )

                    report[
                        "photos"
                    ].append(saved)


            report[
                "items"
            ][key] = {

                "response":
                    form.get(
                        "response_" + key,
                        ""
                    ),

                "observation":
                    form.get(
                        "observation_" + key,
                        ""
                    ),

                "photos":
                    photos

            }


    # ========================================================
    # SIGNATURES
    # ========================================================

    for role,field in [

        (
            "customer",
            "customer_signature"
        ),

        (
            "engineer",
            "engineer_signature"
        )

    ]:


        signature = form.get(
            field,
            ""
        )


        if signature.startswith(
            "data:image"
        ):

            encoded = signature.split(
                ",",
                1
            )[1]


            filename = (
                "signature_"
                + role
                + "_"
                + uuid.uuid4().hex
                + ".png"
            )


            path = (
                UPLOAD_DIR
                / filename
            )


            path.write_bytes(
                base64.b64decode(
                    encoded
                )
            )


            report[
                "signatures"
            ][role] = filename


    # ========================================================
    # CREATE PDF
    # ========================================================

    pdf_file = create_pdf(
        report
    )


    # ========================================================
    # SAVE DATABASE
    # ========================================================

    conn = get_db()


    cursor = conn.execute(
        """
        INSERT INTO reports
        (
            terminal_id,
            work_order,
            visit_date,
            engineer,
            custodian,
            created_at,
            pdf_file,
            json_data
        )

        VALUES
        (
            ?,?,?,?,?,?,?,?
        )
        """,

        (

            report["info"][
                "terminal_id"
            ],

            report["info"][
                "work_order"
            ],

            report["info"][
                "visit_date"
            ],

            report["info"][
                "engineer"
            ],

            report["info"][
                "custodian"
            ],

            datetime.now().isoformat(),

            pdf_file,

            json.dumps(
                report
            )

        )

    )


    report_id = cursor.lastrowid


    conn.commit()

    conn.close()


    return render_template_string(

        HTML.replace(
            "{% block content %}{% endblock %}",

            """

            <div class="card">

            <h1>
            ✅ Checklist Completed
            </h1>

            <p>
            The PM checklist has been successfully completed.
            </p>

            <div class="actions">

            <a
            class="btn primary"
            target="_blank"
            href="/pdf/"""
            + pdf_file
            + """">

            📄 OPEN GENERATED PDF

            </a>


            <a
            class="btn"
            href="/new">

            ➕ New Checklist

            </a>


            <a
            class="btn"
            href="/history">

            📋 History

            </a>

            </div>

            </div>

            """

        )

    )


# ============================================================
# HISTORY
# ============================================================

@app.route("/history")
def history():

    query = request.args.get(
        "q",
        ""
    ).strip()


    conn = get_db()


    if query:

        like = (
            "%"
            + query
            + "%"
        )


        reports = conn.execute(

            """
            SELECT *
            FROM reports

            WHERE terminal_id LIKE ?
            OR work_order LIKE ?
            OR engineer LIKE ?
            OR custodian LIKE ?

            ORDER BY id DESC
            """,

            (
                like,
                like,
                like,
                like
            )

        ).fetchall()

    else:

        reports = conn.execute(

            """
            SELECT *
            FROM reports
            ORDER BY id DESC
            """

        ).fetchall()


    conn.close()


    return render_template_string(

        HISTORY_HTML,

        reports=reports,

        q=query

    )


# ============================================================
# PDF
# ============================================================

@app.route("/pdf/<filename>")
def pdf(filename):

    path = (
        REPORT_DIR
        / filename
    )


    if not path.exists():

        return "PDF not found",404


    return send_file(
        path,
        mimetype="application/pdf",
        as_attachment=False
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    print("")
    print("=" * 60)
    print("CXK PM CHECKLIST SYSTEM")
    print("=" * 60)
    print("")
    print("Open your browser:")
    print("")
    print("http://127.0.0.1:8000")
    print("")
    print("=" * 60)
    print("")


    app.run(
        host="0.0.0.0",
        port=8000,
        debug=True
    )
