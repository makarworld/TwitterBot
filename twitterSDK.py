import base64
from typing import *
import requests
import urllib3
from urllib3.exceptions import ProtocolError
from loguru import logger
import pyuseragents 
import random
import json  

urllib3.disable_warnings()

class CookieManager:
    @staticmethod
    def load_from_str(cookies_str: str) -> dict:
        try:
            if cookies_str.endswith('=='):
                # only if cookies_str is base64 decoded string with list of cookies
                cookies_str = base64.b64decode(cookies_str).decode()
                cookies = json.loads(cookies_str)
                cookies_dict = {x["name"]: x["value"] for x in cookies}
            else:
                # only if cookies_str is string from browser (F12)
                cocs = [x.strip() for x in cookies_str.split(';')]
                cookies_dict = {}
                for c in cocs:
                    k, v = c.split('=', 1)
                    cookies_dict[k] = v
            
            return cookies_dict
        except Exception as e:
            logger._error("[{}] CookieManager.load_from_str -> Error while parsing cookies -> {}".format(e, cookies_str.replace('\n', '').replace('\r', '').replace('\t', '').replace(' ', '')))
    
    @staticmethod
    def load_from_json(cookies_json: List[dict]) -> dict:
        if isinstance(cookies_json, list):
            if cookies_json[0].get("name"):
                return {x["name"]: x["value"] for x in cookies_json}
            return {k: v for x in cookies_json for k, v in x.items()}
        return cookies_json

class ProxyManager:
    @staticmethod
    def load_from_str(proxies_str: str, proxy_type: str = 'http') -> dict:
        return {
            'http': f'{proxy_type}://{proxies_str}',
            'https': f'{proxy_type}://{proxies_str}'
        }

class URLManager:
    home = 'https://twitter.com/home'
    query_ids = 'https://abs.twimg.com/responsive-web/client-web-legacy/main.2f948aea.js'

class DataManager:
    bearer = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
    TweetResultByRestId = "V3vfsYzNEyD9tsf4xoFRgw"
    CreateRetweet       = "ojPdsZsimiJrUGLR1sjUtA"
    FavoriteTweet       = "lI07N6Otwv1PhnEgXILM7A"
    CreateTweet         = "GUFG748vuvmewdXbB5uPKg"
    ModerateTweet       = "pjFnHGVqCjTcZol0xcBJjw"
    DeleteTweet         = "VaenaVgh5q5ih7kvyVjgtg"
    UserTweets          = "Uuw5X2n3tuGE_SatnXUqLA"

    @staticmethod
    def get_query_id(key: str) -> str:
        return DataManager.__dict__.get(key)

def to_query_params(params: dict):
    return '?' + '&'.join([f"{k}={v}" for k, v in params.items()])

def create_random(k: int = 3):
    return "".join(list(
                   random.choices("abcdefghijklmnopqrstuvwxyz013456789", k = k)))


class TwitterSDK:

    def __init__(self, cookies: dict, proxies: dict):
        self.cookies = cookies
        self.proxies = proxies

        self.session = requests.Session()
        self.session.cookies.update(cookies)
        self.session.headers.update({
            'user-agent': pyuseragents.random(),
            'Authorization': DataManager.bearer,
            'x-csrf-token': cookies['ct0'],
            'Origin': 'https://mobile.twitter.com',
            'Referer': 'https://mobile.twitter.com/',
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en',
            'content-type': 'application/json',
            'accept': '*/*',
            'accept-language': 'ru,en;q=0.9,vi;q=0.8,es;q=0.7',
        })

        if proxies:
            self.session.proxies.update(proxies)
        
        # test connection
        self.username = self.get_username()
        if self.username:
            user = self.get_user_by_screen_name(self.username)['data']
            if user.get('user'):
                self.user_id = user['user']['result']['rest_id']
            else:
                logger._warning(f"Fail to get user_id - {self.username}")


            logger.debug(f"Connected to account {self.username} (user_id:{self.user_id}).")



    def call(self, method, url, return_value: Union[None, str] = None, **kwargs) -> requests.Response:
        logger.debug(f"REQUEST | {method} {url} {kwargs}")
        try:
            req = self.session.request(method, url, verify=False, **kwargs)
        except (ConnectionResetError, ProtocolError, requests.exceptions.ConnectionError) as e:
            logger._error(f"{e} -> {self.cookies}")
            return {"errors": [{"message": "ConnectionResetError"}]}

        logger.debug(f"RESPONSE | {req.content}")

        try:
            if req.json().get("errors"):
                if req.json()["errors"][0].get("message") == "Could not authenticate you":
                    logger._error(f"Invalid cookies (ERROR:Could not authenticate you) -> {self.cookies}")
        except:
            pass

        if not return_value:
            return req
        
        if return_value == 'json':
            return req.json()
        
        if return_value == 'text':
            return req.text
        
        if return_value == 'content':
            return req.content
        
        return req
    
    def get_username(self) -> str:
        r = self.call("GET", 'https://mobile.twitter.com/i/api/1.1/account/settings.json',
                      params=dict(
                        include_mention_filter = True,
                        include_nsfw_user_flag = True,
                        include_nsfw_admin_flag = True,
                        include_ranked_timeline = True,
                        include_alt_text_compose = True,
                        ext = 'ssoConnections',
                        include_country_code = True,
                        include_ext_dm_nsfw_media_filter = True,
                        include_ext_sharing_audiospaces_listening_data_with_followers = True
        ), return_value = 'json')

        if r.get('errors'):
            return None
        else:
            return r['screen_name']

    def get_random_username(self) -> dict:
        first3 = create_random(k=3)
        return self.call("GET", 'https://twitter.com/i/api/1.1/search/typeahead.json',
                            params = dict(
                                q = first3,
                                src = 'compose',
                                result_type = 'users',
                                context_text = first3
                            )).json()
    
    def get_followers(self, count: int = 20) -> dict:
        return self.call(
            method = "GET",
            url = "https://twitter.com/i/api/graphql/WWFQL1d4gxtqm2mjZCRa-Q/Followers" 
                  + to_query_params(dict(
                    variables = json.dumps(dict(
                        userId = self.user_id,
                        count = count,
                        includePromotedContent = False
                    ), separators=(',', ':')),
                    features = json.dumps(dict(
                        rweb_lists_timeline_redesign_enabled = True,
                        responsive_web_graphql_exclude_directive_enabled = True,
                        verified_phone_label_enabled = False,
                        creator_subscriptions_tweet_preview_api_enabled = True,
                        responsive_web_graphql_timeline_navigation_enabled = True,
                        responsive_web_graphql_skip_user_profile_image_extensions_enabled = False,
                        tweetypie_unmention_optimization_enabled = True,
                        responsive_web_edit_tweet_api_enabled = True,
                        graphql_is_translatable_rweb_tweet_is_translatable_enabled = True,
                        view_counts_everywhere_api_enabled = True,
                        longform_notetweets_consumption_enabled = True,
                        tweet_awards_web_tipping_enabled = False,
                        freedom_of_speech_not_reach_fetch_enabled = True,
                        standardized_nudges_misinfo = True,
                        tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled = False,
                        longform_notetweets_rich_text_read_enabled = True,
                        longform_notetweets_inline_media_enabled = True,
                        responsive_web_enhance_cards_enabled = False
                    ), separators=(',', ':'))
                  ))
        ).json()

    def get_following(self, count: int = 20) -> dict:
        return self.call(
            method = "GET",
            url = "https://twitter.com/i/api/graphql/OLcddmNLPVXGDgSdSVj0ow/Following" 
                  + to_query_params(dict(
                    variables = json.dumps(dict(
                        userId = self.user_id,
                        count = count,
                        includePromotedContent = False
                    ), separators=(',', ':')),
                    features = json.dumps(dict(
                        rweb_lists_timeline_redesign_enabled = True,
                        responsive_web_graphql_exclude_directive_enabled = True,
                        verified_phone_label_enabled = False,
                        creator_subscriptions_tweet_preview_api_enabled = True,
                        responsive_web_graphql_timeline_navigation_enabled = True,
                        responsive_web_graphql_skip_user_profile_image_extensions_enabled = False,
                        tweetypie_unmention_optimization_enabled = True,
                        responsive_web_edit_tweet_api_enabled = True,
                        graphql_is_translatable_rweb_tweet_is_translatable_enabled = True,
                        view_counts_everywhere_api_enabled = True,
                        longform_notetweets_consumption_enabled = True,
                        tweet_awards_web_tipping_enabled = False,
                        freedom_of_speech_not_reach_fetch_enabled = True,
                        standardized_nudges_misinfo = True,
                        tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled = False,
                        longform_notetweets_rich_text_read_enabled = True,
                        longform_notetweets_inline_media_enabled = True,
                        responsive_web_enhance_cards_enabled = False
                    ), separators=(',', ':'))
                  ))
        ).json()

    def get_random_usernames(self, length: int) -> List[str]:
        users_list = []

        for _ in range(length):
            r = self.get_random_username()
            users_list.append(f"@{r['users'][0]['screen_name']}")
        else:
            return users_list
        
    def get_random_followers(self, length: int) -> List[str]:
        r = self.get_followers(count = 100)

        users = r['data']['user']['result']['timeline']['timeline']['instructions'][-1]['entries']
        users = [x['content']['itemContent']['user_results']['result']['legacy']['screen_name'] for x in users]

        if length > len(users):
            res = ["@" + user for user in users]
            res += self.get_random_usernames(length - len(users))
            return res

        return ["@" + user for user in random.choices(users, k=length)]

    def get_random_followings(self, length: int) -> List[str]:
        r = self.get_following(count = 100)

        users = r['data']['user']['result']['timeline']['timeline']['instructions'][-1]['entries'][:-2]
        users = [x['content']['itemContent']['user_results']['result']['legacy']['screen_name'] for x in users]

        if length > len(users):
            res = ["@" + user for user in users]
            res += self.get_random_usernames(length - len(users))
            return res

        return ["@" + user for user in random.choices(users, k=length)]


    def get_user_by_screen_name(self, username: str) -> dict:
        return self.call(
            method = "GET",
            url = "https://twitter.com/i/api/graphql/qRednkZG-rn1P6b48NINmQ/UserByScreenName" 
                  + to_query_params(dict(
                    variables = json.dumps(dict(
                        screen_name = username,
                        withSafetyModeUserFields = True
                    ), separators=(',', ':')),
                    features = json.dumps(dict(
                        hidden_profile_likes_enabled = False,
                        responsive_web_graphql_exclude_directive_enabled = True,
                        verified_phone_label_enabled = False,
                        subscriptions_verification_info_verified_since_enabled = True,
                        highlights_tweets_tab_ui_enabled = True,
                        creator_subscriptions_tweet_preview_api_enabled = True,
                        responsive_web_graphql_skip_user_profile_image_extensions_enabled = False,
                        responsive_web_graphql_timeline_navigation_enabled = True
                    ), separators=(',', ':'))
                  )),
            headers = {
                'content-type': 'application/x-www-form-urlencoded'
            }).json()

    def __follow_action(self, user_id: str, action: Literal['create', 'destroy']) -> requests.Response:
        return self.call(
            method = "POST",
            url = f"https://twitter.com/i/api/1.1/friendships/{action}.json",
            data = dict(
                include_profile_interstitial_type = 1,
                include_blocking = 1,
                include_blocked_by = 1,
                include_followed_by = 1,
                include_want_retweets = 1,
                include_mute_edge = 1,
                include_can_dm = 1,
                include_can_media_tag = 1,
                include_ext_has_nft_avatar = 1,
                include_ext_is_blue_verified = 1,
                include_ext_verified_type = 1,
                include_ext_profile_image_shape = 1,
                skip_status = 1,
                user_id = user_id,
                ),
                headers = {
                    'content-type': 'application/x-www-form-urlencoded' 
                }
            )

    def follow(self, author: str = None, user_id: int = None) -> dict:
        if not author and not user_id:
            raise ValueError("Either author or user_id must be provided.")
        
        if not user_id:
            user = self.get_user_by_screen_name(author)['data']
            if user.get('user'):
                user_id = user['user']['result']['rest_id']
            else:
                raise ValueError("User not found.")

        return self.__follow_action(user_id, 'create').json()
    
    def unfollow(self, author: str = None, user_id: int = None) -> dict:
        if not author and not user_id:
            raise ValueError("Either author or user_id must be provided.")
        
        if not user_id:
            user = self.get_user_by_screen_name(author)['data']
            if user.get('user'):
                user_id = user['user']['result']['rest_id']
            else:
                raise ValueError("User not found.")
            
        return self.__follow_action(user_id, 'destroy').json()
    
    def __tweet_action(self, tweet_id: int, action: Literal["CreateRetweet", "FavoriteTweet"]) -> requests.Response:
        query_id = DataManager.get_query_id(action)
        return self.call(
            method = "POST",
            url = f'https://twitter.com/i/api/graphql/{query_id}/{action}',
            json = dict(
                variables = dict(
                    tweet_id = tweet_id,
                    dark_request = False
                ),
                queryId = query_id
            ),
            headers = {'content-type': 'application/json'}
        )

    def retweet(self, tweet_id: int) -> dict:
        return self.__tweet_action(tweet_id, 'CreateRetweet').json()

    def like(self, tweet_id: int) -> dict:
        return self.__tweet_action(tweet_id, 'FavoriteTweet').json()
    
    def __tweet_actionv2(self, text: int, tweet_id: int = None) -> requests.Response:
        action = "CreateTweet"
        query_id = DataManager.get_query_id(action)
        _json = dict(
            variables = dict(
                tweet_text = text,
                media = dict(
                    media_entities = [],
                    possibly_sensitive = False
                ),
                semantic_annotation_ids = [],
                dark_request = False
            ),
            features = dict(
                freedom_of_speech_not_reach_fetch_enabled = True,
                graphql_is_translatable_rweb_tweet_is_translatable_enabled = True,
                longform_notetweets_consumption_enabled = True,
                longform_notetweets_inline_media_enabled = True,
                longform_notetweets_rich_text_read_enabled = True,
                responsive_web_edit_tweet_api_enabled = True,
                responsive_web_enhance_cards_enabled = False,
                responsive_web_graphql_exclude_directive_enabled = True,
                responsive_web_graphql_skip_user_profile_image_extensions_enabled = False,
                responsive_web_graphql_timeline_navigation_enabled = True,
                standardized_nudges_misinfo = True,
                tweet_awards_web_tipping_enabled = False,
                tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled = False,
                tweetypie_unmention_optimization_enabled = True,
                verified_phone_label_enabled = False,
                view_counts_everywhere_api_enabled = True
            ),
            queryId = query_id)
        
        if tweet_id:
            _json['variables']['reply'] = dict(
                in_reply_to_tweet_id = tweet_id,
                exclude_reply_user_ids = []
            )

        return self.call(
            method = "POST",
            url = f'https://twitter.com/i/api/graphql/{query_id}/{action}',
            json = _json,
            headers = {
                'content-type': 'application/json'
            })
    

    def tweet(self, text: str) -> dict:
        return self.__tweet_actionv2(text).json()

    def comment(self, tweet_id: int, text: str) -> dict:
        return self.__tweet_actionv2(text, tweet_id).json()

    def advanced_comment(self, tweet_id: int, text: str, mark_count: int, mark_type: int) -> dict:
        if mark_count > 0:
            if mark_type == 1: # random
                text += " " + " ".join(self.get_random_usernames(mark_count))
            elif mark_type == 2: # followers
                text += " " + " ".join(self.get_random_followers(mark_count))
            elif mark_type == 3: # followings
                text += " " + " ".join(self.get_random_followings(mark_count))

        return self.__tweet_actionv2(text, tweet_id).json()

    def delete_tweet(self, tweet_id: int) -> dict:
        return self.call(
            method = "POST",
            url = "https://twitter.com/i/api/graphql/VaenaVgh5q5ih7kvyVjgtg/DeleteTweet",
            json = dict(
                variables = dict(
                    tweet_id = tweet_id,
                    dark_request = False
                ),
                queryId = "VaenaVgh5q5ih7kvyVjgtg"
            )
        ).json()
    
    def get_tweet(self, tweet_id: int) -> dict:
        return self.call(
            method = "GET",
            url = "https://twitter.com/i/api/graphql/VWFGPVAGkZMGRKGe3GFFnA/TweetDetail" +
            to_query_params({
                "variables": json.dumps(dict(
                    focalTweetId = tweet_id,
                    with_rux_injections = False,
                    includePromotedContent = True,
                    withCommunity = True,
                    withQuickPromoteEligibilityTweetFields = True,
                    withBirdwatchNotes = True,
                    withVoice = True,
                    withV2Timeline = True
                ), separators=(',', ':')),
                "features": json.dumps(dict(
                    rweb_lists_timeline_redesign_enabled = True,
                    responsive_web_graphql_exclude_directive_enabled = True,
                    verified_phone_label_enabled = False,
                    creator_subscriptions_tweet_preview_api_enabled = True,
                    responsive_web_graphql_timeline_navigation_enabled = True,
                    responsive_web_graphql_skip_user_profile_image_extensions_enabled = False,
                    tweetypie_unmention_optimization_enabled = True,
                    responsive_web_edit_tweet_api_enabled = True,
                    graphql_is_translatable_rweb_tweet_is_translatable_enabled = True,
                    view_counts_everywhere_api_enabled = True,
                    longform_notetweets_consumption_enabled = True,
                    tweet_awards_web_tipping_enabled = False,
                    freedom_of_speech_not_reach_fetch_enabled = True,
                    standardized_nudges_misinfo = True,
                    tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled = False,
                    longform_notetweets_rich_text_read_enabled = True,
                    longform_notetweets_inline_media_enabled = True,
                    responsive_web_enhance_cards_enabled = False
                ), separators=(',', ':'))
            }),
        ).json()

    def change_username(self, new_username: str) -> dict:
        return self.call(
            method = "POST",
            url = 'https://twitter.com/i/api/1.1/account/settings.json',
            data = dict(
                include_mention_filter = True,
                include_nsfw_user_flag = True,
                include_nsfw_admin_flag = True,
                include_ranked_timeline = True,
                include_alt_text_compose = True,
                screen_name = new_username
            ),
            headers = {
                'content-type': 'application/x-www-form-urlencoded'
            }
        ).json()

    def change_avatar(self, avatar_data: str) -> dict:
        return self.call(
            method = "POST",
            url = "https://twitter.com/i/api/1.1/account/update_profile_image.json",
            data = {"image": avatar_data},
            headers = {'content-type': 'application/x-www-form-urlencoded'},
        ).json()

    def change_banner(self, banner_data: str) -> dict:
        return self.call(
            method = "POST",
            url = "https://twitter.com/i/api/1.1/account/update_profile_banner.json",
            data = {"banner": banner_data},
            headers = {'content-type': 'application/x-www-form-urlencoded'},
        ).json()
    
if __name__ == "__main__":
    with open('accounts.txt', 'r') as f:
        cookies_str = f.readlines()[0].strip()
    cookies = CookieManager.load_from_str(cookies_str)
    proxy = ProxyManager.load_from_str('EpGqhU:UqbN7a@38.170.123.2:8000')
    t = TwitterSDK(cookies, proxy)
    tweet1 = t.advanced_comment(1666834220138766340, "Damn", 2, 1)
    print(tweet1)
    #print(tweet1.get('followind'))#.get('errors'))#['data']['threaded_conversation_with_injections_v2']['instructions'][0]['entries'][0])
