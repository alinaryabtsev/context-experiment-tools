"""
This is a participant tracking script of the context reward experiment.
The only lines that should be changed in order to run this script are lines 15 and 16 and maybe 17.
author - Alina Ryabtsev
email - alina.ryabtsev@mail.huji.ac.il
version - 1.0.3"
"""
import sys
from datetime import datetime
from datetime import timedelta
import time
import sqlite3
import os

DB_FILE_NAME = "2007_schedule.db"  # Put the database file name within the quotation marks
DATA_FROM_TODAY = False  # Put True if today's data, False if data is from yesterday
DAYS_DELTA = 1  # number of prior days to take data from

MAX_EXPERIMENT_DAYS = 12
MORNING_HOURS = (5, 11)
AFTERNOON_HOURS = (12, 17)
EVENING_HOURS = (18, 23)
MORNING_SESSION = "morning session"
AFTERNOON_SESSION = "afternoon session"
EVENING_SESSION = "evening session"
NO_SESSION = "no session"
BLOCKS = "blocks"
REMOVE_MS = 1000  # python cannot handle timestamp with milliseconds, so we need to remove them.
SECONDS_IN_A_DAY = 86400
FELL_ASLEEP = "fell asleep"
WOKE_UP = "woke up"
TIME_FORMAT = "%d-%m-%Y %H:%M:%S"


TODAY = "today"
YESTERDAY = "yesterday"

SQL_QUERY_SLEEP_DIARY = {
    TODAY:     "SELECT event,time,date FROM 'sleep' WHERE strftime('%Y-%m-%d', "
               "datetime(time/1000, 'unixepoch')) = date(CURRENT_TIMESTAMP) "
               "Order By time DESC LIMIT 2",
    YESTERDAY: f"SELECT event,time,date FROM 'sleep' WHERE strftime('%Y-%m-%d', datetime(time/1000,"
               f" 'unixepoch')) = date('now','-{DAYS_DELTA} days') Order By time DESC LIMIT 2"
}

SQL_QUERY_MOOD_REPORT = {
    TODAY:     "SELECT answer_time FROM 'answers' WHERE questionnaire_type=0 AND question=2 AND "
               "strftime('%Y-%m-%d', datetime(answer_time/1000, 'unixepoch')) = "
               "date(CURRENT_TIMESTAMP) ORDER BY questionnaire_number asc LIMIT 3",
    YESTERDAY: f"SELECT answer_time FROM 'answers' WHERE questionnaire_type=0 AND question=2 AND "
               f"strftime('%Y-%m-%d', datetime(answer_time/1000, 'unixepoch')) = "
               f"date('now','-{DAYS_DELTA} days') ORDER BY questionnaire_number asc LIMIT 3"
}

SQL_QUERY_VIDEO_RECORDING = {
    TODAY:     "SELECT answer_time FROM 'answers' WHERE questionnaire_type=21 AND "
               "strftime('%Y-%m-%d', datetime(answer_time/1000, 'unixepoch')) = "
               "date(CURRENT_TIMESTAMP) ORDER BY questionnaire_number desc LIMIT 1",
    YESTERDAY: f"SELECT * FROM 'answers' WHERE questionnaire_type=21 AND strftime('%Y-%m-%d', "
               f"datetime(answer_time/1000, 'unixepoch')) = date('now','-{DAYS_DELTA} days') ORDER "
               f"BY questionnaire_number desc LIMIT 1"
}

SQL_QUERY_GAMES = {
    TODAY:     "SELECT choice_time, scheduled_time, block FROM 'trials' WHERE trial=31 AND "
               "strftime('%Y-%m-%d', datetime(choice_time/1000, 'unixepoch')) = date("
               "CURRENT_TIMESTAMP) ORDER BY block DESC LIMIT 4",
    YESTERDAY: f"SELECT choice_time, scheduled_time, block FROM 'trials' WHERE trial=31 AND "
               f"strftime('%Y-%m-%d', datetime(choice_time/1000, 'unixepoch')) = "
               f"date('now','-{DAYS_DELTA} days') ORDER BY block DESC LIMIT 4"
}


class TimesHelper:
    """
    This class is in charge of calculating time differences
    """

    def __init__(self):
        self.now = datetime.fromtimestamp(int(time.time()))

    @staticmethod
    def convert_timestamp_to_readable(timestamp):
        """
        :param timestamp: timestamp
        :return: a string converted from UTC timestamp to %d-%m-%Y %H:%M:%S
        """
        return datetime.fromtimestamp(int(timestamp)).strftime(TIME_FORMAT)

    def is_today_timestamp(self, ts):
        """
        :param ts: timestamp
        :return: True if timestamp is from today, else False
        """
        if self.now.date() != datetime.fromtimestamp(ts).date():
            return False
        return True

    @staticmethod
    def is_morning_timestamp(ts):
        """
        :param ts: timestamp
        :return: True if timestamp is considered as a morning hour, else False
        """
        hour = datetime.fromtimestamp(ts).hour
        if MORNING_HOURS[0] <= hour <= MORNING_HOURS[1]:
            return True
        return False

    @staticmethod
    def is_afternoon_timestamp(ts):
        """
        :param ts: timestamp
        :return: True if timestamp is considered as an afternoon hour, else False
        """
        hour = datetime.fromtimestamp(ts).hour
        if AFTERNOON_HOURS[0] <= hour <= AFTERNOON_HOURS[1]:
            return True
        return False

    @staticmethod
    def is_evening_timestamp(ts):
        """
        :param ts: timestamp
        :return: True if timestamp is considered as an evening hour, else False
        """
        hour = datetime.fromtimestamp(ts).hour
        if EVENING_HOURS[0] <= hour <= EVENING_HOURS[1]:
            return True
        return False

    @staticmethod
    def get_time_diff_of_two_timestamps(ts1, ts2):
        """
        :param ts1: first timestamp
        :param ts2: second timestamp
        :return: time difference of both timestamps
        """
        return str(datetime.fromtimestamp(int(ts1)) - datetime.fromtimestamp(int(ts2)))

    @staticmethod
    def get_time_diff_of_two_times(ts1, ts2):
        """
        :param ts1: string representing time in format of "%d-%m-%Y %H:%M:%S"
        :param ts2: string representing time in format of "%d-%m-%Y %H:%M:%S"
        :return: time difference of both times
        """
        return str(abs(datetime.strptime(ts1, TIME_FORMAT) - datetime.strptime(ts2, TIME_FORMAT)))


class DataBaseData:
    """
    This class is in charge of managing database file and taking data from it.
    """

    def __init__(self, file_path):
        """
        Initializes data base reader object
        :param file_path: the path of the database file
        """
        if not os.path.exists(file_path):
            print(f"No database file have been found. Please make sure the data base file is "
                  f"named as {file_path} and can be found where the script is.")
            sys.exit()
        self.conn = sqlite3.connect(file_path)
        self.curr = self.conn.cursor()
        self.times_helper = TimesHelper()

    def get_sleep_diary_reports(self, to_check=TODAY):
        """
        :return: if sleep diary reports filled right, then should return a dictionary
                    {"woke up" : date, "fell asleep" : date}
                else it will return an empty dictionary
        """
        self.curr.execute(SQL_QUERY_SLEEP_DIARY[to_check])
        times = self.curr.fetchall()
        sleep_diary = dict()
        for t in times:
            if t[0] not in sleep_diary:
                sleep_diary[t[0]] = t[2]
        return sleep_diary

    def get_mood_reports(self, to_check=TODAY):
        """
        :return: returns a dictionary of mood reports activity as follows:
        {"morning session" : [timestamp of the last morning session or the last third session
                              completed or emptystring]
        ... (same with afternoon and evening sessions. If executed in another time - will be
        attached to no session tag)
        }
        """
        self.curr.execute(SQL_QUERY_MOOD_REPORT[to_check])
        times = self.curr.fetchall()
        times = [t[0] / REMOVE_MS for t in times]
        reports = {MORNING_SESSION: "", AFTERNOON_SESSION: "", EVENING_SESSION: "", NO_SESSION: ""}
        for t in times:
            if self.times_helper.is_morning_timestamp(t) and not reports[MORNING_SESSION]:
                reports[MORNING_SESSION] = self.times_helper.convert_timestamp_to_readable(t)
            elif self.times_helper.is_afternoon_timestamp(t) and not reports[AFTERNOON_SESSION]:
                reports[AFTERNOON_SESSION] = self.times_helper.convert_timestamp_to_readable(t)
            elif self.times_helper.is_evening_timestamp(t) and not reports[EVENING_SESSION]:
                reports[EVENING_SESSION] = self.times_helper.convert_timestamp_to_readable(t)
            else:
                reports[NO_SESSION] = self.times_helper.convert_timestamp_to_readable(t)
        return reports

    def has_recorded_video_recording(self, to_check=TODAY):
        """
        :return: true if today's video has been recorded.
        """
        self.curr.execute(SQL_QUERY_VIDEO_RECORDING[to_check])
        time_executed = self.curr.fetchall()
        if time_executed:
            return True
        return False

    def get_games_play_report(self, to_check=TODAY):
        """
        :return: a dictionary as follows:
                {"some session" : [(time the first trial executed,
                                    time difference between scheduled to executed),
                                    (time the second trial executed,
                                    time difference between scheduled to executed)] }
        """
        self.curr.execute(SQL_QUERY_GAMES[to_check])
        times = self.curr.fetchall()
        times = [[x / REMOVE_MS for x in t] for t in times]
        games_played = {MORNING_SESSION: [], EVENING_SESSION: [], NO_SESSION: [], BLOCKS: []}
        for t in times:
            games_played[BLOCKS].append(int(t[2] * 1000))  # for some reason it's divided by 1000
            ls = (self.times_helper.convert_timestamp_to_readable(t[0]),
                  self.times_helper.get_time_diff_of_two_timestamps(t[0], t[1]))
            if self.times_helper.is_morning_timestamp(t[0]) and \
                    len(games_played[MORNING_SESSION]) < 2:
                games_played[MORNING_SESSION].append(ls)
            elif self.times_helper.is_evening_timestamp(t[0]) and \
                    len(games_played[EVENING_SESSION]) < 2:
                games_played[EVENING_SESSION].append(ls)
            else:
                games_played[NO_SESSION].append(ls)
        games_played[BLOCKS].sort()
        return games_played


def generate_analysis_text(db, data_from=TODAY):
    """
    :param data_from: a string which represents if the data is from today ("today") or from
    yesterday ("yesterday")
    :param db: the database file to get data from.
    :return: an output text.
    """
    if data_from == TODAY:
        txt = f"DAILY TRACKING ANALYSIS - {datetime.utcnow().date()}\n\n"
    else:
        txt = f"DAILY TRACKING ANALYSIS - {datetime.utcnow().date() - timedelta(days=DAYS_DELTA)}\n\n"
    mood_reports = db.get_mood_reports(data_from)
    sleep_diary = db.get_sleep_diary_reports(data_from)
    games_played = db.get_games_play_report(data_from)
    txt += "MOOD REPORTS:\n"
    for session, data in mood_reports.items():
        if session == NO_SESSION:
            if data:
                txt += f"  Some session completed at {data}, but not in scheduled time.\n"
        elif data:
            txt += f"  Completed {session} mood report at {data}.\n"
        else:
            txt += f"  Has not completed {session} mood report.\n"
    txt += "\nSLEEP DIARY:\n"
    if sleep_diary:
        for action, data in sleep_diary.items():
            txt += f"  {action} at {data}.\n"
    else:
        txt += "  No sleeping data added.\n"
    txt += "\nVIDEO RECORDINGS:\n"
    if db.has_recorded_video_recording(data_from):
        txt += "  Has completed a video recording.\n"
    else:
        txt += "  Has not completed a video recording.\n"
    txt += "\nGAMES PERFORMANCE:\n"
    blocks = games_played.pop(BLOCKS)
    if blocks:
        txt += f"  Blocks played: " + ", ".join([str(n) for n in blocks]) + ".\n"
    for session, data in games_played.items():
        if session == NO_SESSION:
            if len(data) >= 1:
                for i in range(len(data)):
                    txt += f"  Has completed a game but not in time, at {data[i][0]} with delay " \
                           f"of {data[i][1]}.\n"
        elif data and len(data) >= 1:
            txt += f"  Has completed {session} game at {data[0][0]} with delay of {data[0][1]}.\n"
            if len(data) >= 2:
                txt += f"  Has completed another {session} game at {data[1][0]} with delay of " \
                       f"{data[1][1]}.\n"
                txt += f"  * Time difference between first and second {session} games is " \
                       f"{TimesHelper.get_time_diff_of_two_times(data[0][0], data[1][0])}.\n"
            else:
                txt += f"  Has not completed the second game of the {session}.\n"
        else:
            txt += f"  No games of the {session} have been completed.\n"
    return txt


def main():
    """
    Opens a file to write in the results of monitoring according to current UTC time (since the
    timestamps of the data are in UTC time format.
    :return:
    """
    if DAYS_DELTA > MAX_EXPERIMENT_DAYS:
        raise ValueError(f"Specified DAYS_DELTA value {DAYS_DELTA} is bigger than"
                         f" {MAX_EXPERIMENT_DAYS}")
    db = DataBaseData(DB_FILE_NAME)
    if DATA_FROM_TODAY:
        with open(f"{DB_FILE_NAME}_analysis_{datetime.utcnow().date()}.txt", "w") as output:
            output.write(generate_analysis_text(db, TODAY))
    else:
        with open(f"{DB_FILE_NAME}_analysis_{datetime.utcnow().date() - timedelta(days=DAYS_DELTA)}.txt", "w") as output:
            output.write(generate_analysis_text(db, YESTERDAY))


if __name__ == "__main__":
    main()
