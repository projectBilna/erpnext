# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr, cint
from frappe import msgprint, _
import MySQLdb
import datetime

now = datetime.datetime.now()
holidays = [datetime.date(now.year, 8, 17), datetime.date(now.year, 12, 25), 
			datetime.date(now.year, 1, 1), datetime.date(now.year, 1, 3),
			datetime.date(now.year, 2, 19), datetime.date(now.year, 3, 21),
			datetime.date(now.year, 4, 3), datetime.date(now.year, 5, 1),
			datetime.date(now.year, 5, 14), datetime.date(now.year, 5, 16),
			datetime.date(now.year, 6, 2), datetime.date(now.year, 7, 17),
			datetime.date(now.year, 7, 18), datetime.date(now.year, 9, 24),
			datetime.date(now.year, 10, 14), datetime.date(now.year, 7, 16),
			datetime.date(now.year, 7, 20), datetime.date(now.year, 7, 21),
			datetime.date(now.year, 12, 24)
			] # you can add more here
businessdays = 0
for i in range(1, 32):
    try:
        thisdate = datetime.date(now.year, now.month, i)
    except(ValueError):
        break
    if thisdate.weekday() < 5 and thisdate not in holidays: # Monday == 0, Sunday == 6 
        businessdays += 1

def execute(filters=None):
	if not filters: filters = {}

	conditions, filters = get_conditions(filters)
	columns = get_columns(filters)
	att_map = get_attendance_list(conditions, filters)
	emp_map = get_employee_details()
	data = []
	department_attendance={}
	
	for emp in sorted(att_map):
		emp_det = emp_map.get(emp)
		if not emp_det:
			continue
			
		average = 0
		total_p = total_a = 0.0
		total_in_secs=[]
		for day in range(filters["total_days_in_month"]):
			status = att_map.get(emp).get(day + 1, "Absent")
			status_map = {"Present": "P", "Absent": "A", "Half Day": "HD"}
			time= (att_map.get(emp).get("time").get(day + 1))
			if time != None:
				l = str(time).split(':')
				total_in_secs.append(int(l[0]) * 3600 + int(l[1]) * 60 + int(l[2]))
			

			if status == "Present":
				total_p += 1
			elif status == "Absent":
				total_a += 1
			elif status == "Half Day":
				total_p += 0.5
				total_a += 0.5

		
		average = total_p/businessdays * 100 
		average_print = str(round(average,2))+"%"
		t=0
		for y in xrange(0, len(total_in_secs)):
			t += total_in_secs[y]
			average_time = t/total_p/3600

		row = [emp, emp_det.employee_name, total_p, total_a , average_print , round(average_time,1),emp_det.branch, emp_det.department, emp_det.designation]
			
		for day in range(filters["total_days_in_month"]):
			status = att_map.get(emp).get(day + 1, "Absent")
			status_map = {"Present": "P", "Absent": "A", "Half Day": "HD"}
			row.append(status_map[status])
		
		department_attendance.setdefault(emp_det.department,[]).append(round(average_time,1))
		
		data.append(row)
		
	for key in department_attendance:
		total = 0
		for num in department_attendance[key]:
			total += num
			
		totalx = total/len(department_attendance[key])
		
		print 'Department : %s %s' % (key, department_attendance[key])
		print 'Total : %s' % totalx
		
	return columns, data

def get_columns(filters):

	columns = [
		_("Employee") + ":Link/Employee:120", _("Employee Name") + "::140"
		 #_("Company") + ":Link/Company:120"
		 , _("Total Present") + ":Float:80", _("Total Absent") + ":Float:80",_("Average Present day") + "::100",_("Average Working Hours") + "::140", _("Branch")+ ":Link/Branch:120",
		_("Department") + ":Link/Department:120", _("Designation") + ":Link/Designation:120" ]
		
	for day in range(filters["total_days_in_month"]):
		columns.append(cstr(day+1) +"::20")
	return columns


def get_attendance_list(conditions, filters):
	attendance_list = frappe.db.sql("""select employee, day(att_date) as day_of_month,
		status,time_in, time_out from tabAttendance where docstatus = 1 %s order by employee, att_date""" %
		conditions, filters, as_dict=1)
		
	att_map = {}
	for d in attendance_list:
		att_map.setdefault(d.employee, frappe._dict()).setdefault(d.day_of_month, "")
		att_map[d.employee][d.day_of_month] = d.status
		att_map.setdefault(d.employee, frappe._dict()).setdefault("time", frappe._dict()).setdefault(d.day_of_month, "")
		att_map[d.employee]["time"][d.day_of_month] = d.time_out - d.time_in
		
	return att_map

def get_conditions(filters):
	if not (filters.get("month") and filters.get("fiscal_year")):
		msgprint(_("Please select month and year"), raise_exception=1)

	filters["month"] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov",
		"Dec"].index(filters["month"]) + 1

	from frappe.model.document import Document
	fiscal_years = frappe.get_doc("Fiscal Year",filters["fiscal_year"])
	import datetime
	year_start = fiscal_years.year_start_date.strftime("%Y")
	year_end = fiscal_years.year_end_date.strftime("%Y")
	dt_test = datetime.datetime.strptime(year_end + "-" + str(100+int(filters["month"]))[2:3] + "-01", "%Y-%m-%d")
	date_test = datetime.date(dt_test.year, dt_test.month, dt_test.day)
	if date_test > fiscal_years.year_end_date:
		year_target = year_start
	else:
		year_target = year_end

	from calendar import monthrange
	filters["total_days_in_month"] = monthrange(cint(year_target),
		filters["month"])[1]

	conditions = " and month(att_date) = %(month)s and fiscal_year = %(fiscal_year)s"

	#if filters.get("company"): conditions += " and company = %(company)s"
	if filters.get("employee"): conditions += " and employee = %(employee)s"

	return conditions, filters

def get_employee_details():
	emp_map = frappe._dict()
	for d in frappe.db.sql("""select name, employee_name, designation,
		department, branch, company
		from tabEmployee where docstatus < 2
		and status = 'Active'""", as_dict=1):
		emp_map.setdefault(d.name, d) 

	return emp_map
	

	
