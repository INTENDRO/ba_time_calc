import os
import sys
import matplotlib.pyplot as plt
import seaborn as sns
import csv
import re
import time
import collections
import datetime
import statistics
import argparse



############################################################################
# REGEX
############################################################################

re_pat_date = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
re_pat_time = re.compile(r"(\d{1,2})[\.:](\d{1,2})\s*-\s*(\d{1,2})[\.:](\d{1,2})\s(\d)\s(.*)")

############################################################################

def get_home_dir():
	return os.path.dirname(os.path.realpath(__file__))

def config_sns():
	sns.set(style="darkgrid")

def parse_console_arguments():
	# parse input arguments
	parser = argparse.ArgumentParser()
	parser.add_argument("-d", "--date",
					dest="filename",
					required=False,
					help="specify the date of the file. default: newest file")

	cli_args = parser.parse_args()

	return cli_args

def get_filepaths(home_dir, cli_args):
	if cli_args.filename is not None:
		filename = cli_args.filename
		if not filename.endswith(".txt"):
			filename = filename+".txt"
	else: #get newest file
		files = os.listdir(os.path.join(home_dir,"data"))
		filename = sorted(files)[-1]

	filepath = os.path.join(home_dir,"data\\"+filename)
	csv_filepath = filepath[:-3] + "csv"

	return (filepath, csv_filepath)

def parse_raw_to_csv(filepath, csv_filepath):
	current_day = None

	with open(filepath, "r") as readf, open(csv_filepath,"w",newline="") as writef:
		csv_writer = csv.writer(writef)


		for idx,line in enumerate(readf):
			if line.strip() == "":
				continue

			result = re_pat_date.findall(line)
			if result: #date
				current_day = list(reversed((result)[0]))
				continue

			result = re_pat_time.findall(line)
			if result: #time data
				if current_day is None:
					raise Exception("Time data found before the first date line!")

				result = list(result[0])
				result[4] = result[4].strip()

				csv_writer.writerow(current_day + result)

				continue

			# could not parse line
			print("Could not parse line {}: {}".format(idx+1,line),end="")

def get_time_sets(csv_filepath):

	# global stats (e.g total, average, etcs)
	time_stats = {"total_time": 0}

	# get the time for every day
	day_time_dict = collections.OrderedDict()

	# get the time for every week
	week_time_dict = collections.OrderedDict()

	# get the time for every subject
	subject_time_dict = collections.OrderedDict()

	# get the time for every weekday 
	weekday_time_dict = collections.OrderedDict() # 1: Monday ... 7: Sunday

	# get each individual times for all the different weekday. this is needed for the weekday average
	weekday_detailed_time_dict = collections.OrderedDict()

	# get the average time for every weekday
	weekday_avg_time_dict = collections.OrderedDict() # 1: Monday ... 7: Sunday

	# get the individual quality and length of work blocks for every weekday
	weekday_detailed_quality_dict = collections.OrderedDict()

	# get the average work quality for every weekday
	weekday_avg_quality_dict = collections.OrderedDict() # 1: Monday ... 7: Sunday


	with open(csv_filepath,"r",newline="") as f:
		csv_reader = csv.reader(f)

		for idx,line in enumerate(csv_reader):
			current_day = line[0]+line[1]+line[2] # represent day as string. e.g.: "20181011"
			year,weeknumber,weekday = datetime.date(int(line[0]),int(line[1]),int(line[2])).isocalendar()
			start_minutes = int(line[3])*60 + int(line[4])
			stop_minutes = int(line[5])*60 + int(line[6])
			work_quality = int(line[7])
			subject = line[8]

			time_delta = stop_minutes - start_minutes

			time_stats["total_time"] += time_delta # in minutes


			try:
				day_time_dict[current_day] += time_delta
			except KeyError: # new day!
				day_time_dict[current_day] = 0
				day_time_dict[current_day] += time_delta

			try:
				week_time_dict[weeknumber] += time_delta
			except KeyError: # new day!
				week_time_dict[weeknumber] = 0
				week_time_dict[weeknumber] += time_delta
				
			try:
				subject_time_dict[subject] += time_delta
			except KeyError: # new subject
				subject_time_dict[subject] = 0
				subject_time_dict[subject] += time_delta

			try:
				weekday_time_dict[weekday] += time_delta
			except KeyError: # new weekday
				weekday_time_dict[weekday] = 0
				weekday_time_dict[weekday] += time_delta

			try:
				weekday_detailed_time_dict[weekday].append(time_delta) # accumulate all detailed times and later devide by week count
			except KeyError: # new weekday
				weekday_detailed_time_dict[weekday] = []
				weekday_detailed_time_dict[weekday].append(time_delta)

			try:
				weekday_detailed_quality_dict[weekday].append((time_delta, work_quality))
			except KeyError: # new weekday
				weekday_detailed_quality_dict[weekday] = []
				weekday_detailed_quality_dict[weekday].append((time_delta, work_quality))

	


	time_stats["longest_week_time"] = max(list(week_time_dict.values()))
	time_stats["longest_day_time"] = max(list(day_time_dict.values()))
	# check the next two calculations!
	# time_stats["average_week_time"] = round(statistics.mean(list(week_time_dict.values())))
	temp = list(week_time_dict.values())
	time_stats["average_week_time"] = round(sum(temp) / len(temp))
	# time_stats["average_week_time_wo_current"] = round(statistics.mean(list(week_time_dict.values())[:-1]))
	temp = list(week_time_dict.values())[:-1]
	time_stats["average_week_time_wo_current"] = round(sum(temp) / len(temp))

	time_stats["total_weekcount"] = list(week_time_dict.keys())[-1] - list(week_time_dict.keys())[0] + 1

	for key,val in weekday_detailed_time_dict.items():
		weekday_avg_time_dict[key] = sum(val)/time_stats["total_weekcount"]

	for key,val in weekday_detailed_quality_dict.items():
		weighted_sum = 0
		total_time = 0
		for time,quality in val:
			total_time += time
			weighted_sum += time*quality

		weekday_avg_quality_dict[key] = weighted_sum / total_time

	return (time_stats, day_time_dict, week_time_dict, subject_time_dict, weekday_time_dict, weekday_detailed_time_dict, weekday_avg_time_dict, weekday_detailed_quality_dict, weekday_avg_quality_dict)

def display_day_time(day_time_dict):
	day_time_day_list = []
	day_time_time_list = []

	for key,val in day_time_dict.items():
		day_time_day_list.append(key)
		day_time_time_list.append(val/60)


	fig,ax = plt.subplots()
	# ax.bar(day_time_day_list,day_time_time_list)
	sns.barplot(day_time_day_list,day_time_time_list,ax=ax,palette="Blues_d")


def display_week_time(week_time_dict):
	week_time_time_list = []
	week_time_weeknum_list =[]

	for key,val in week_time_dict.items():
		week_time_weeknum_list.append(key)
		week_time_time_list.append(val/60)

	fig,ax = plt.subplots()
	# ax.bar(day_time_day_list,day_time_time_list)
	ax = sns.barplot(week_time_weeknum_list,week_time_time_list,ax=ax,palette="Blues_d")
	# locks,labels = plt.xticks()
	# plt.xticks(locks,labels,rotation=20)
	ax.set(xlabel="Kalenderwoche",ylabel="Arbeitsstunden")


def display_subject_time(subject_time_dict):
	subject_time_time_list = []
	subject_time_subject_list =[]

	for key,val in subject_time_dict.items():
		subject_time_subject_list.append(key)
		subject_time_time_list.append(val/60)


	fig,ax = plt.subplots()
	# ax.bar(day_time_day_list,day_time_time_list)
	sns.barplot(subject_time_subject_list,subject_time_time_list,ax=ax,palette="Blues_d")
	locks,labels = plt.xticks()
	plt.xticks(locks,labels,rotation=20)

def display_weekday_time(weekday_time_dict):
	weekday_time_list = [0]*7

	for key,val in weekday_time_dict.items():
		weekday_time_list[key-1] = (val/60)

	fig,ax = plt.subplots()
	# ax.bar(day_time_day_list,day_time_time_list)
	ax = sns.barplot(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],weekday_time_list,ax=ax,palette="Blues_d")
	# locks,labels = plt.xticks()
	# plt.xticks(locks,labels,rotation=20)
	ax.set(xlabel="Wochentag",ylabel="Arbeitsstunden")

def display_weekday_avg_time(weekday_avg_time_dict):
	weekday_time_list = [0]*7

	for key,val in weekday_avg_time_dict.items():
		weekday_time_list[key-1] = (val/60)

	fig,ax = plt.subplots()
	# ax.bar(day_time_day_list,day_time_time_list)
	ax = sns.barplot(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],weekday_time_list,ax=ax,palette="Blues_d")
	# locks,labels = plt.xticks()
	# plt.xticks(locks,labels,rotation=20)
	ax.set(xlabel="Wochentag",ylabel="Arbeitsstunden")

def display_weekday_avg_quality(weekday_avg_quality_dict):
	weekday_quality_list = [0]*7

	for key,val in weekday_avg_quality_dict.items():
		weekday_quality_list[key-1] = (val)

	fig,ax = plt.subplots()
	# ax.bar(day_time_day_list,day_time_time_list)
	ax = sns.barplot(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],weekday_quality_list,ax=ax,palette="Blues_d")
	# locks,labels = plt.xticks()
	# plt.xticks(locks,labels,rotation=20)
	ax.set(xlabel="Wochentag",ylabel="Qualität")

def main():
	home_dir = get_home_dir()
	os.chdir(home_dir)

	cli_args = parse_console_arguments()

	config_sns()

	filepath, csv_filepath = get_filepaths(home_dir, cli_args)

	print(filepath)
	print(csv_filepath)

	parse_raw_to_csv(filepath, csv_filepath)

	time_stats, day_time_dict, week_time_dict, subject_time_dict, weekday_time_dict, weekday_detailed_time_dict, weekday_avg_time_dict, weekday_detailed_quality_dict, weekday_avg_quality_dict = get_time_sets(csv_filepath)

	print("Total time: {}min <-> {}hr {}min".format(time_stats["total_time"],time_stats["total_time"]//60,time_stats["total_time"]%60))
	print("Longest day: {}min <-> {}hr {}min".format(time_stats["longest_day_time"],time_stats["longest_day_time"]//60,time_stats["longest_day_time"]%60))
	print("Longest week: {}min <-> {}hr {}min".format(time_stats["longest_week_time"],time_stats["longest_week_time"]//60,time_stats["longest_week_time"]%60))
	print("Average week: {}min <-> {}hr {}min".format(time_stats["average_week_time"],time_stats["average_week_time"]//60,time_stats["average_week_time"]%60))
	print("Average week (without current): {}min <-> {}hr {}min".format(time_stats["average_week_time_wo_current"],time_stats["average_week_time_wo_current"]//60,time_stats["average_week_time_wo_current"]%60))
	print("Total week count: {}".format(time_stats["total_weekcount"]))


	display_day_time(day_time_dict)
	display_week_time(week_time_dict)
	display_subject_time(subject_time_dict)
	display_weekday_time(weekday_time_dict)
	display_weekday_avg_time(weekday_avg_time_dict)
	display_weekday_avg_quality(weekday_avg_quality_dict)
	plt.show()
	sys.exit(0)



if __name__ == "__main__":
	main()
