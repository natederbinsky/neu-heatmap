from flask import Flask, request, redirect, url_for

from neubanner import banner

import html
import base64
import operator
import collections

app = Flask(__name__)

##############################################################################
##############################################################################

def _out(l):
	return "\n".join(l)

def _has_needed_post(l):
	for n in l:
		if n not in request.form:
			return False
	return True

def _has_needed_get(l):
	for n in l:
		if n not in request.args:
			return False
	return True

##############################################################################
##############################################################################

ANALYTICS_ID = None
SITE_TITLE = 'Northeastern HeatMap'

def _header(ret, title):
	ret.append('<!DOCTYPE html><html lang="en"><head>')
	ret.append('<meta charset="utf-8">')
	ret.append('<meta http-equiv="X-UA-Compatible" content="IE=edge">')
	ret.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
	ret.append('<link rel="shortcut icon" href="{}" type="image/x-icon"><link rel="icon" href="{}" type="image/x-icon">'.format(url_for('static', filename='favicon.ico'),url_for('static', filename='favicon.ico')))
	ret.append('<link href="{}" rel="stylesheet">'.format(url_for('static', filename="bootstrap.css")))
	ret.append('<title>{} - {}</title>'.format(html.escape(SITE_TITLE), html.escape(title)))
	if ANALYTICS_ID:
		ret.append("<script>(function(i,s,o,g,r,a,m){{i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){{(i[r].q=i[r].q||[]).push(arguments)}},i[r].l=1*new Date();a=s.createElement(o),m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)}})(window,document,'script','https://www.google-analytics.com/analytics.js','ga'); ga('create', '{}', 'auto');ga('send', 'pageview');</script>".format(html.escape(ANALYTICS_ID)))
	ret.append('</head><body><div class="container">')
	ret.append('<h1>{}</h1>'.format(html.escape(title)))

def _footer(ret, exit=True):
	if exit:
		ret.append('<br /><br />')
		ret.append('<small><a class="hidden-print" href="/logout">EXIT</a></small>')
	ret.append('</div>')
	ret.append('<br /><br />')
	ret.append('</body></html>')

##############################################################################
##############################################################################

_DAYS = collections.OrderedDict()
_DAYS["M"] = "Monday"
_DAYS["T"] = "Tuesday"
_DAYS["W"] = "Wednesday"
_DAYS["R"] = "Thursday"
_DAYS["F"] = "Friday"

def _demo_search_time(slot):
	ampm = "am" if slot < 120 else "pm"
	slot -= 0 if slot < 130 else 120
	m = "30" if (slot // 5) % 2 == 1 else "00"
	h = slot // 10
	return "{}:{} {}".format(h, m, ampm)

def _demo_search_color(count, numprofs):
	if count == 0:
		return ""
	elif count == 1:
		return "bg-info"
	elif count >= numprofs/2:
		return "bg-danger"
	else:
		return "bg-warning"

def _demo_time_to_index(t, start):
	hrm,ampm = t.split(" ")
	hr,m = (int(x) for x in hrm.split(":"))
	isam = ampm=="am"

	index = hr
	if isam is False and hr < 12:
		index += 12

	index *= 10
	if m > 30:
		index += 5

	if start:
		if m == 30:
			index += 5

	if not start:
		if m == 0:
			index -= 5

	return index

def _demo_facultyschedule(instructors, days):
	if not instructors:
		return

	codes = banner.searchcodes()
	profs = [p[0] for p in instructors]

	params = {"subject":codes["sel_subj"].keys()}
	params["instructor"] = profs

	sections = banner.sectionsearch(**params)

	for section in sections:
		for classmtg in section["meetings"]:
			for day in classmtg['days']:
				for tf in range(_demo_time_to_index(classmtg['times'][0], True), _demo_time_to_index(classmtg['times'][1], False)+1, 5):
					if tf>=80 and tf<200:
						days[day][tf].add(section["spans"]["Instructors"])


def _demo_studentschedule(students, days):
	for student in students:
		xyz = banner.getxyz_studid(student)
		banner.idset(xyz)
		schedule = banner.studentschedule()
		for entry in schedule:
			for meeting in entry["meetings"]:
				for day in meeting["days"]:
					for tf in range(_demo_time_to_index(meeting["times"][0], True), _demo_time_to_index(meeting["times"][1], False)+1, 5):
						if tf>=80 and tf<200:
							days[day][tf].add(student)

def demo_schedule(instructors, students):
	days = {d:{t:set() for t in range(80, 200, 5)} for d in _DAYS.keys()}

	_demo_facultyschedule(instructors, days)
	_demo_studentschedule(students, days)

	return days

##############################################################################
##############################################################################

@app.route('/', methods=['POST', 'GET'])
def login(msg=None):
	if request.headers.get('X-Forwarded-Proto') == "http":
		return redirect(request.url.replace('http://', 'https://', 1), code=301)

	banner.logout()

	ret = []
	_header(ret, 'Login')

	if msg:
		ret.append('<p class="bg-danger">{}</b>'.format(msg))
	ret.append('<form method="POST" action="login">')
	ret.append('<div class="form-group">')
	ret.append('<label id="user">User name</label>')
	ret.append('<input type="text" id="user" class="form-control" name="user" placeholder="myNortheastern Username" />')
	ret.append('</div>')
	ret.append('<div class="form-group">')
	ret.append('<label id="pw">Password</label>')
	ret.append('<input type="password" id="pw" class="form-control" name="pw" placeholder="myNortheastern Password" />')
	ret.append('</div>')
	ret.append('<input type="submit" class="btn btn-primary" value="Login" />')
	ret.append('</form>')

	_footer(ret, exit=False)

	return _out(ret)

@app.route('/logout', methods=['POST', 'GET'])
def logout():
	return login("Logged out!")

@app.route('/login', methods=['POST'])
def term():
	if request.headers.get('X-Forwarded-Proto') == "http":
		return redirect(request.url.replace('http://', 'https://', 1), code=301)

	if not _has_needed_post(("user","pw",)):
		return login()

	if not banner.login(u=request.form["user"], p=request.form["pw"]):
		return login("Login failed!")

	##

	terms = banner.termdict()

	##

	ret = []
	_header(ret, 'Select Term')

	ret.append('<form action="people" method="POST">')
	ret.append('<input type="hidden" name="sid" value="{}" />'.format(base64.b64encode(banner.savestate()).decode('ASCII')))

	ret.append('<div class="form-group">')
	ret.append('<label id="term">Term</label>')
	now = 'foorbar'
	ret.append('<select name="term" id="term" class="form-control">')
	for code,name in sorted(terms.items(), key=operator.itemgetter(0), reverse=True):
		if code:
			ret.append('<option {}value="{}">{}</option>'.format('selected="selected" ' if code==now else '', html.escape(code), html.escape(name)))
	ret.append('</select>')
	ret.append('</div>')

	ret.append('<input type="submit" class="btn btn-primary" value="Submit" />')

	ret.append('</form>')

	_footer(ret)

	return _out(ret)

@app.route('/people', methods=['POST'])
def people():
	if request.headers.get('X-Forwarded-Proto') == "http":
		return redirect(request.url.replace('http://', 'https://', 1), code=301)

	if not _has_needed_post(("sid",)):
		return login()

	banner.loadstate(base64.b64decode(request.form["sid"].encode('ASCII')))
	if _has_needed_post(("term",)):
		banner.termset(request.form["term"])

	##

	codes = banner.searchcodes()

	##

	ret = []
	_header(ret, 'Select People')

	ret.append('<form action="search" method="POST">')
	ret.append('<input type="hidden" name="sid" value="{}" />'.format(base64.b64encode(banner.savestate()).decode('ASCII')))

	ret.append('<div class="form-group">')
	ret.append('<label id="profs">Faculty</label>')
	ret.append('<select id="profs" name="profs" multiple="multiple" size="20" class="form-control">')
	for code,name in sorted(codes["sel_instr"].items(), key=operator.itemgetter(1)):
		if name != "All":
			ret.append('<option value="{}">{}</option>'.format(html.escape(code + '|' + name), html.escape(name)))
	ret.append('</select>')
	ret.append('</div>')


	ret.append('<div class="form-group">')
	ret.append('<label id="students">NUIDs (separated by whitespace)</label>')
	ret.append('<textarea id="students" name="students" rows="20" class="form-control">')
	ret.append('</textarea>')
	ret.append('</div>')

	ret.append('<input type="submit" class="btn btn-primary" value="Submit" />')

	ret.append('</form>')

	_footer(ret)

	return _out(ret)

@app.route('/search', methods=['POST'])
def search():
	if request.headers.get('X-Forwarded-Proto') == "http":
		return redirect(request.url.replace('http://', 'https://', 1), code=301)

	if not _has_needed_post(("sid",)):
		return login()

	banner.loadstate(base64.b64decode(request.form["sid"].encode('ASCII')))

	##

	profslist = [x.split('|') for x in request.form.getlist("profs")]
	studentslist = request.form["students"].split()

	days = demo_schedule(profslist, studentslist)
	num = len(profslist) + len(studentslist)

	day_names = list(days.keys())
	slot_names = sorted(days[day_names[0]].keys())

	##

	ret = []
	_header(ret, 'Heatmap')

	if profslist:
		ret.append('<h4>Faculty ({}) <small>'.format(len(profslist)) + html.escape('; '.join(["{} ({})".format(p[1], p[0]) for p in profslist])) + '</small></h4>')

	if studentslist:
		ret.append('<h4>Students ({}) <small>'.format(len(studentslist)) + html.escape('; '.join(studentslist)) + '</small></h4>')

	ret.append('<div class="row"><div class="table-responsive"><table class="table table-bordered table-condensed" style="width: auto !important">')

	ret.append('<tr>')
	ret.append('<th width="80px"></th>')
	for d,name in _DAYS.items():
		ret.append('<th width="120px" class="text-center">{}</th>'.format(html.escape(name)))
	ret.append('</tr>')

	for slot in slot_names:
		ret.append('<tr>')
		ret.append('<th>{}</th>'.format(html.escape(_demo_search_time(slot))))
		for d in _DAYS.keys():
			count = len(days[d][slot])
			ret.append('<td title="{}" class="text-center {}">{}</td>'.format(html.escape("; ".join(days[d][slot])), _demo_search_color(count, num), html.escape(str(count) if count > 0 else "")))
		ret.append('</tr>')

	ret.append('</table></div><div>')

	ret.append('<div class="row">')
	ret.append('<form action="people" method="POST">')
	ret.append('<input type="hidden" name="sid" value="{}" />'.format(base64.b64encode(banner.savestate()).decode('ASCII')))
	ret.append('<input type="submit" class="btn btn-primary hidden-print" value="Search Again" />')
	ret.append('</form>')
	ret.append('</div>')

	_footer(ret)

	return _out(ret)

if __name__ == '__main__':
	app.run()
