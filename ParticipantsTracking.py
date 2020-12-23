from datetime import datetime

import time
import sqlite3
import os
import sys

DB_FILE_NAME = "001_schedule.db"
MORNING_HOURS = (5, 12)
AFTERNOON_HOURS = (12, 17)
EVENING_HOURS = (17, 23)
MORNING_SESSION = "morning session"
AFTERNOON_SESSION = "afternoon session"
EVENING_SESSION = "evening session"
REMOVE_MS = 1000  # python cannot handle timestamp with milliseconds, so we need to remove them.
SECONDS_IN_A_DAY = 86400
FELL_ASLEEP = "fell asleep"
WOKE_UP = "woke up"

class TimesHelper:
    def __init__(self):
        self.now = datetime.fromtimestamp(int(time.time()))

    @staticmethod
    def convert_timestamp_to_readable(timestamp):
        return datetime.fromtimestamp(int(timestamp)).strftime('%d-%m-%Y %H:%M:%S')

    def is_today_timestamp(self, ts):
        if self.now.date() != datetime.fromtimestamp(ts).date:
            return False
        return True

    def is_morning_timestamp(self, ts):
        hour = datetime.fromtimestamp(ts).hour
        if self.is_today_timestamp(ts) and MORNING_HOURS[0] < hour < MORNING_HOURS[1]:
            return True
        return False

    def is_afternoon_timestamp(self, ts):
        hour = datetime.fromtimestamp(ts).hour
        if self.is_today_timestamp(ts) and AFTERNOON_HOURS[0] <= hour <= AFTERNOON_HOURS[1]:
            return True
        return False

    def is_evening_timestamp(self, ts):
        hour = datetime.fromtimestamp(ts).hour
        if self.is_today_timestamp(ts) and EVENING_HOURS[0] <= hour <= EVENING_HOURS[1]:
            return True
        return False

    @staticmethod
    def get_time_diff_of_two_timestamps(ts1, ts2):
        return str(datetime.fromtimestamp(int(ts1)) - datetime.fromtimestamp(int(ts2)))


class DataBaseData:
    def __init__(self, file_path):
        if file_path not in os.listdir(os.getcwd()):
            print(f"No database file have been found. Please make sure the data base file is "
                  f"named as {file_path} and can be found where the script is.")
            sys.exit()
        self.conn = sqlite3.connect(file_path)
        self.curr = self.conn.cursor()
        self.times_helper = TimesHelper()

    def get_sleep_diary_reports(self):
        """
        :return: if sleep diary reports filled right, then should return a dictionary
                    {"woke up" : date, "fell asleep" : date}
                else it will return an empty dictionary
        """
        self.curr.execute("SELECT event,time,date FROM 'sleep' Order By time DESC LIMIT 2")
        times = self.curr.fetchall()
        sleep_diary = dict()
        for t in times:
            if t[0] not in sleep_diary and self.times_helper.is_today_timestamp(t[1] / REMOVE_MS):
                sleep_diary[t[0]] = t[2]
        return sleep_diary

    def get_mood_reports(self):
        """
        :return: returns a dictionary of mood reports activity as follows:
        {"morning session" : [true if morning session has been completed else false,
                              timestamp of the last morning session or the last third session
                              completed]
        ... (same with afternoon and evening sessions)
        }
        """
        self.curr.execute("SELECT answer_time FROM 'answers' WHERE questionnaire_type=0 AND "
                          "question=2 ORDER BY questionnaire_number desc LIMIT 3")
        times = self.curr.fetchall()
        times = [t[0] / REMOVE_MS for t in times]
        reports_activity = \
            {MORNING_SESSION: [self.times_helper.is_morning_timestamp(times[2]),
                               self.times_helper.convert_timestamp_to_readable(times[2])],
             AFTERNOON_SESSION: [self.times_helper.is_afternoon_timestamp(times[1]),
                                 self.times_helper.convert_timestamp_to_readable(times[1])],
             EVENING_SESSION: [self.times_helper.is_evening_timestamp(times[0]),
                               self.times_helper.convert_timestamp_to_readable(times[0])]}
        return reports_activity

    def is_video_recording(self):
        """
        :return: true if today's video has been recorded.
        """
        self.curr.execute("SELECT answer_time FROM 'answers' WHERE questionnaire_type=21 ORDER BY "
                          "questionnaire_number desc LIMIT 1")
        time_executed = self.curr.fetchall()[0][0]
        if self.times_helper.is_today_timestamp(time_executed / REMOVE_MS):
            return True
        return False

    def get_games_play_report(self):
        """
        :return: a dictionary as follows:
                {"some session" : [(true if first trial executed today,
                                    time the trial executed,
                                    time difference between scheduled to executed),
                                    (true if second trial executed today,
                                    time the trial executed,
                                    time difference between scheduled to executed)] }
        """
        self.curr.execute("SELECT choice_time,scheduled_time FROM 'trials' WHERE trial=71 AND "
                          "stim_time>0 ORDER BY block DESC LIMIT 4")
        times = self.curr.fetchall()
        times = [[x / REMOVE_MS for x in t] for t in times]
        games_report = \
            {MORNING_SESSION: [(self.times_helper.is_today_timestamp(times[3][0]),
                               self.times_helper.convert_timestamp_to_readable(times[3][0]),
                               self.times_helper.get_time_diff_of_two_timestamps(times[3][0],
                                                                                 times[3][1])),
                               (self.times_helper.is_today_timestamp(times[2][0]),
                               self.times_helper.convert_timestamp_to_readable(times[2][0]),
                               self.times_helper.get_time_diff_of_two_timestamps(times[2][0],
                                                                                 times[2][1]))],
             EVENING_SESSION: [(self.times_helper.is_today_timestamp(times[1][0]),
                               self.times_helper.convert_timestamp_to_readable(times[1][0]),
                               self.times_helper.get_time_diff_of_two_timestamps(times[1][0],
                                                                                 times[1][1])),
                               (self.times_helper.is_today_timestamp(times[0][0]),
                               self.times_helper.convert_timestamp_to_readable(times[0][0]),
                               self.times_helper.get_time_diff_of_two_timestamps(times[0][0],
                                                                                 times[0][1]))]}
        return games_report


def main():
    db = DataBaseData(DB_FILE_NAME)
    rows = db.get_mood_reports()
    print(f"mood reports: {rows}")
    print(f"sleep diary: {db.get_sleep_diary_reports()}")
    print(f"video recorded: {db.is_video_recording()}")
    print(f"games played: {db.get_games_play_report()}")


if __name__ == "__main__":
    main()
