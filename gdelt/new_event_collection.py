import psycopg2
import urllib2
from six.moves import configparser
from smart_open import smart_open
from pprint import pprint

class Database_Operations(object):

    def __init__(self, config):
        config.read('config.ini')
        self.__db_name = config.get('dbauth', 'dbname')
        self.__db_user = config.get('dbauth', 'user')
        self.__db_pass = config.get('dbauth', 'password')
        self.__db_host = config.get('dbauth', 'host')
        self.__db_port = config.get('dbauth', 'port')


    """
        All commands should be sent to this function execute
    """
    def db_command(self, commands):

        conn = None
        try:
            # connect to postgresql server
            conn = psycopg2.connect("dbname=" + self.__db_name+ \
                                    " host=" + self.__db_host+ \
                                    " port= " + self.__db_port+ \
                                    " user=" + self.__db_user+ \
                                    " password=" + self.__db_pass)
            cur = conn.cursor()

            # to get results for each operation
            results = []

            # execute each command
            for comm in commands:
                cur.execute(comm)
                results.append(cur.fetchall())
            cur.close()
            conn.commit()
        except(Exception, psycopg2.DatabaseError) as error:
            print 'DB Error - ' + str(error)
        finally:
            if conn is not None:
                conn.close()
                return results


    def create_gdelt_table(self):

        command = [
        """CREATE TABLE gdelt_events (
            globaleventid INTEGER PRIMARY KEY, sqldate INTEGER,
            actor1code VARCHAR(10), actor1name VARCHAR(50),
            actor1geo_fullname VARCHAR(100), actor1countrycode VARCHAR(10),
            actor2code VARCHAR(10), actor2name VARCHAR(50),
            actor2geo_fullname VARCHAR(100), actor2countrycode VARCHAR(10),
            goldstein_scale NUMERIC, avg_tone NUMERIC, num_mentions INTEGER,
            event_code VARCHAR(10), source_url VARCHAR(200)
        );"""]

        results = self.db_command(command)
        pprint(results)


class Data_Gatherer(object):

    def __init__(self):
        # Super important link, updated every 15 minutes
        self.target_url = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
        self.target_file = None
        self.primary_fields = ['GLOBALEVENTID', 'SQLDATE', 'MonthYear', \
            'Year', 'FractionDate', 'Actor1Code', 'Actor1Name', \
            'Actor1CountryCode', 'Actor1KnownGroupCode', 'Actor1EthnicCode', \
            'Actor1Religion1Code', 'Actor1Religion2Code', 'Actor1Type1Code', \
            'Actor1Type2Code','Actor1Type3Code','Actor2Code', 'Actor2Name', \
            'Actor2CountryCode', 'Actor2KnownGroupCode', 'Actor2EthnicCode', \
            'Actor2Religion1Code', 'Actor2Religion2Code', 'Actor2Type1Code', \
            'Actor2Type2Code', 'Actor2Type3Code', 'IsRootEvent', 'EventCode', \
            'EventBaseCode', 'EventRootCode', 'QuadClass', 'GoldsteinScale', \
            'NumMentions', 'NumSources', 'NumArticles', 'AvgTone', \
            'Actor1Geo_Type', 'Actor1Geo_FullName', 'Actor1Geo_CountryCode', \
            'Actor1Geo_ADM1Code', 'gap_1', 'Actor1Geo_Lat', 'Actor1Geo_Long', \
            'Actor1Geo_FeatureID', 'Actor2Geo_Type', 'Actor2Geo_FullName', \
            'Actor2Geo_CountryCode', 'gap_2', 'Actor2Geo_ADM1Code', \
            'Actor2Geo_Lat', 'Actor2Geo_Long', 'Actor2Geo_FeatureID', \
            'ActionGeo_Type', 'ActionGeo_FullName', 'ActionGeo_CountryCode', \
            'ActionGeo_ADM1Code', 'gap_3', 'ActionGeo_Lat', 'ActionGeo_Long', \
            'ActionGeo_FeatureID', 'DATEADDED', 'SOURCEURL']


    def set_target_file(self):

        target_file_link = None

        data = urllib2.urlopen(self.target_url)
        for line in data:
            target_file_link = line
            break

        # file size, hash, link to zip
        target_link = target_file_link.split(" ")[2]
        target_file = target_link.split("/")[-1]
        target_filename = target_file.replace(".zip\n", "")
        print 'Target file - ' + target_file

        self.target_file = target_filename


    def generate_sql_command(self, record):

        globaleventid = record['GLOBALEVENTID']
        sqldate = record['SQLDATE']
        actor1code = "'"+record['Actor1Code']+"'"
        actor1name = "'"+record['Actor1Name']+"'"
        actor1geo_fullname = "'"+record['Actor1Geo_FullName']+"'"
        actor1countrycode = "'"+record['Actor1Geo_CountryCode']+"'"
        actor2code = "'"+record['Actor2Code']+"'"
        actor2name = "'"+record['Actor2Name']+"'"
        actor2geo_fullname = "'"+record['Actor2Geo_FullName']+"'"
        actor2countrycode = "'"+record['Actor2Geo_CountryCode']+"'"
        goldstein_scale = record['GoldsteinScale']
        avg_tone = record['AvgTone']
        num_mentions = record['NumMentions']
        event_code = "'"+record['EventCode']+"'"
        source_url = "'"+record['SOURCEURL']+"'"


        command = "INSERT INTO gdelt_events( \
            globaleventid, sqldate, actor1code, actor1name, actor1geo_fullname, \
            actor1countrycode, actor2code, actor2name, actor2geo_fullname, \
            actor2countrycode, goldstein_scale, avg_tone, num_mentions, event_code, \
            source_url) \
            VALUES("+str(globaleventid)+","+str(sqldate)+","+actor1code+","+actor1name+","+ \
            actor1geo_fullname+","+actor1countrycode+","+actor2code+","+actor2name+","+ \
            actor2geo_fullname+","+actor2countrycode+","+str(goldstein_scale)+","+ \
            str(avg_tone)+","+str(num_mentions)+","+str(event_code)+","+source_url+");"

        return command

    def read_s3_file_contents(self, data_ops_handler, target=None):

        commands = []
        # for line in smart_open('s3://gdelt-open-data/v2/events/'+target, 'rb'):
        for line in smart_open('s3://gdelt-open-data/v2/events/'+self.target_file, 'rb'):
            line = line.split('\t')

            dict_line = dict(zip(self.primary_fields, line))
            # pprint(dict_line)

            commands.append(self.generate_sql_command(dict_line))

        results = data_ops_handler.db_command(commands)
        print 'Added events for file -' + self.target_file
        print '\tNumber of commands - ' + str(len(commands))
        print '\tNumber of results - ' + str(len(results))



def example_psql_query(db_ops, ton_select):
    
    command = ["SELECT * FROM gdelt_events WHERE gdelt_events.avg_tone < " + \
                str(tone_select) + "ORDER BY gdelt_events.sqldate DESC;"]

    results = db_ops.db_command(command)
    pprint(results)



if __name__ == '__main__':

    config = configparser.ConfigParser()
    db_ops = Database_Operations(config)
    data_gather = Data_Gatherer()

    data_gather.set_target_file()

    # db_ops.create_gdelt_table()
    # data_gather.read_s3_file_contents(db_ops, "20190124233000.export.csv")
    data_gather.read_s3_file_contents(db_ops)

    # tone_select = -15.0
    # example_psql_query(db_ops, tone_select)

    print 'Done'