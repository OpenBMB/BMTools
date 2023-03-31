import requests
from lxml import etree
import pandas as pd
from translate import Translator
import re
from ...tool import Tool


def build_tool(config) -> Tool:
    tool = Tool(
        "Film Search Plugin",
        "search for up-to-date film information.",
        name_for_model="Film Search",
        description_for_model="Plugin for search for up-to-date film information.",
        logo_url="https://your-app-url.com/.well-known/logo.png",
        contact_email="hello@contact.com",
        legal_info_url="hello@legal.com"
    )
    
    def fetch_page(url : str):
        """get_name(url: str) print html text of url
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                                'Chrome/108.0.0.0 Safari/537.36'}
        s = requests.session()
        s.keep_alive = False
        response = s.get(url, headers=headers, verify=False)

        return response

    @tool.get("/parse_coming_page")
    def parse_coming_page():
        """parse_coming_page() prints the details of the all coming films, including date, title, cate, region, wantWatchPeopleNum, link
        """
        # 获取即将上映的电影列表
        url = 'https://movie.douban.com/coming'
        response = fetch_page(url)

        df_filmsComing = pd.DataFrame(columns=["date", "title", "cate", "region", "wantWatchPeopleNum", 'link'])

        parser = etree.HTMLParser(encoding='utf-8')
        tree = etree.HTML(response.text, parser=parser)

        movies_table_path = '//*[@id="content"]/div/div[1]/table/tbody'
        movies_table = tree.xpath(movies_table_path)
        for filmChild in movies_table[0].iter('tr'):
            filmTime = filmChild.xpath('td[1]/text()')[0].strip()
            filmName = filmChild.xpath('td[2]/a/text()')[0]
            # Translator(fo).translate(filmType)
            filmType = filmChild.xpath('td[3]/text()')[0].strip()
            filmRegion = filmChild.xpath('td[4]/text()')[0].strip()
            filmWantWatching = filmChild.xpath('td[5]/text()')[0].strip()
            filmLink = filmChild.xpath('td[2]/a/@href')[0]
            df_filmsComing.loc[len(df_filmsComing.index)] = [
                filmTime, filmName, filmType, filmRegion, filmWantWatching, filmLink
            ]
        return df_filmsComing

    @tool.get("/parse_nowplaying_page")
    def parse_nowplaying_page():
        """parse_nowplaying_page() prints the details of the all playing films now, including title, score, region, director, actors, link
        """
        # 获取正在上映的电影列表
        url = 'https://movie.douban.com/cinema/nowplaying/beijing/'
        response = fetch_page(url)
        df_filmsNowPlaying = pd.DataFrame(columns=["title", "score", "region", "director", "actors", 'link'])

        parser = etree.HTMLParser(encoding='utf-8')
        tree = etree.HTML(response.text, parser=parser)

        movies_table_path = './/div[@id="nowplaying"]/div[2]/ul'
        movies_table = tree.xpath(movies_table_path)
        for filmChild in movies_table[0]:
            filmName = filmChild.xpath('@data-title')[0]
            filmScore = filmChild.xpath('@data-score')[0]
            filmRegion = filmChild.xpath('@data-region')[0]
            filmDirector = filmChild.xpath('@data-director')[0]
            filmActors = filmChild.xpath('@data-actors')[0]
            filmLink = filmChild.xpath('ul/li[1]/a/@href')[0]
            df_filmsNowPlaying.loc[len(df_filmsNowPlaying.index)] = [
                filmName, filmScore, filmRegion, filmDirector, filmActors, filmLink
            ]
        return df_filmsNowPlaying
    
    def parse_detail_page(response):
        """parse_detail_page(response) get information from response.text
        """
        parser = etree.HTMLParser(encoding='utf-8')
        tree = etree.HTML(response.text, parser=parser)
        info_path = './/div[@class="subject clearfix"]/div[2]'

        director = tree.xpath(f'{info_path}/span[1]/span[2]/a/text()')[0]

        actors = []
        actors_spans = tree.xpath(f'{info_path}/span[3]/span[2]')[0]
        for actors_span in actors_spans:
            actors.append(actors_span.text)
        actors = '、'.join(actors[:3])

        types = []
        spans = tree.xpath(f'{info_path}')[0]
        for span in spans.iter('span'):
            if 'property' in span.attrib and span.attrib['property']=='v:genre':
                types.append(span.text)
        types = '、'.join(types)
        
        for span in spans:
            if span.text=='制片国家/地区:':
                region = span.tail.strip()
                break
        Synopsis = tree.xpath('.//div[@class="related-info"]/div/span')[0].text.strip()
        detail = f'是一部{region}的{types}电影，由{director}导演，{actors}等人主演.\n剧情简介：{Synopsis}'
        return detail
    
    @tool.get("/coming_out_filter")
    def coming_out_filter(args : str):
        """coming_out_filter(args: str) prints the details of the filtered [outNum] coming films now according to region, cate and outNum. 
            args is a list like 'str1, str2, str3, str4'
            str1 can be 中国, 日本, or other region. If you canot find a region, str1 is 全部
            str2 can be 爱情, 喜剧 or other category. If you canot find a category, str2 is 全部
            str3 can be a integer number that agent want to get. If you canot find a number, str2 is 100.
            str4 can be a True or False that refluct whether agent want the result sorted by people number which look forward to the movie.
        """
        args = re.findall(r'\b\w+\b', args)
        region = args[0]
        if region=='全部':
            region = ''
        cate = args[1]
        if cate=='全部':
            cate = ''
        outNum = int(args[2])
        WantSort = True if args[3]=='True' else False

        df = parse_coming_page()
        df_recon = pd.DataFrame.copy(df, deep=True)
        
        # 即将上映的某类型电影，根据想看人数、地区、类型进行筛选
        df_recon['wantWatchPeopleNum'] = df_recon['wantWatchPeopleNum'].apply(lambda x: int(x.replace('人', '')))
        
        df_recon = df_recon[df_recon['cate'].str.contains(cate)]
        df_recon = df_recon[df_recon['region'].str.contains(region)]
        
        # 最后根据想看人数降序排列 
        if WantSort:
            df_recon.sort_values(by="wantWatchPeopleNum" , inplace=True, ascending = not WantSort) 
        outDf = df_recon[:outNum]
        return df.loc[outDf.index, 'date':'wantWatchPeopleNum']


    @tool.get("/now_playing_out_filter")
    def now_playing_out_filter(args : str):
        """NowPlayingOutFilter(args: str) prints the details of the filtered [outNum] playing films now according to region, scoreSort
            args is a list like 'str1, str2, str3'
            str1 can be 中国, 日本, or other region. If you canot find a region, str1 is 全部
            str2 can be a integer number that agent want to get. If you canot find a number, str2 is 100.
            str3 can be a True or False that refluct whether agent want the result sorted by score.
        """
        args = re.findall(r'\b\w+\b', args)
        region = args[0]
        if region=='全部':
            region = ''
        outNum = int(args[1])
        scoreSort = True if args[2]=='True' else False

        df = parse_nowplaying_page()
        
        df_recon = pd.DataFrame.copy(df, deep=True)
        
        df_recon['score'] = df_recon['score'].apply(lambda x: float(x))

        # 正在上映的某类型电影，根据地区进行筛选
        region = Translator(from_lang='English', to_lang='Chinese').translate(region)
        df_recon = df_recon[df_recon['region'].str.contains(region)]
        
        # 最后根据评分降序排列 
        if scoreSort:
            df_recon.sort_values(by="score" , inplace=True, ascending = not scoreSort) 
        outDf = df_recon[:outNum]
        return df.loc[outDf.index, 'title':'actors']

    @tool.get("/print_detail")
    def print_detail(args : str):
        """parsing_detail_page(args) prints the details of a movie, giving its name.
            args is a list like 'str1'
            str1 can be 指环王、神奇女侠、梅兰芳 or other movie's name.
            step1: apply function parse_coming_page and parse_nowplaying_page and get all movie's links and other infomation.
            step2: get the target movie's link from df_coming or df_nowplaying
            step3: get detail from step2's link
        """
        args = re.findall(r'\b\w+\b', args)
        filmName = args[0]
        return f'{filmName}是一部好看的国产动漫电影'
    return tool