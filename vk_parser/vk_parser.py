import vk_api
from private_configurations import LOGIN, PASSWORD, AUTH2CODE


class VKAuthHandler:
    def __init__(self, login: str, password: str, auth2step=False):
        """
        :param login: str
        :param password: str
        :param auth2step: bool
        """
        self.vk_session = vk_api.vk_api.VkApi(login=login, password=password,
                                              auth_handler=self._input_auth_code_ if auth2step else None)
        try:
            self.vk_session.auth()
        except vk_api.AuthError as error_msg:
            print(error_msg)
            exit(1)

    @staticmethod
    def _input_auth_code_():
        """
        :return: auth code: str, remember device: bool
        """
        return str(input("Enter authentication code: ")), True


class VKParserHandler:
    def __init__(self, vk_session: vk_api.vk_api.VkApi):
        """
        :param vk_session: vk_api.vk_api.VkApi
        """
        self.vk_session = vk_session

    def parse_user_friends(self, ids: list):
        """
        :param ids:
        :return:
        """
        ### OLD ###
        # friends = {}
        # with vk_api.VkRequestsPool(vk_session) as pool:
        #     for user_id in ids:
        #         friends[user_id] = pool.method('friends.get', {
        #             'user_id': user_id,
        #             'fields': 'photo'
        #         })
        # for key in friends.keys():
        #     if not friends[key].ok:
        #         # del friends[key]
        #         print(friends[key].error)
        #     else:
        #         print(friends[key].result)

        ### NEW ###
        friends, errors = vk_api.vk_request_one_param_pool(
            self.vk_session,
            'friends.get',  # Метод
            key='user_id',  # Изменяющийся параметр
            values=ids,
            # Параметры, которые будут в каждом запросе
            default_values={'fields': 'photo'}
        )

        return friends, errors

    def parse_user_pages(self, ids: list):
        """
        :param ids:
        :return:
        """
        def parse_user_pages_1000_ids(ids1000: list):
            assert len(ids1000) <= 1000, ValueError("Len `ids1000` should be <= 1000")
            vk = self.vk_session.get_api()
            return vk.users.get(user_ids=ids1000,
                                fields=['blacklisted', 'deactivated', 'is_closed', 'can_access_closed', 'sex', 'bdate',
                                        'country', 'has_photo', 'last_seen', 'photo_max_orig', 'contacts'])

        res = []
        split_ids = [ids[i:i + 1000] for i in range(0, len(ids), 1000)]
        for batch in split_ids:
            res += parse_user_pages_1000_ids(batch)
        return res

    def parse_user_photos(self, ids: list):
        """
        :param ids:
        :return:
        """
        def parse_album(user_id: int, album: str):
            return pool.method('photos.get', {
                'owner_id': user_id,
                'rev': 1,
                'album_id': album
            })

        with vk_api.VkRequestsPool(self.vk_session) as pool:
            res = {user_id: (parse_album(user_id, 'wall'), parse_album(user_id, 'profile')) for user_id in ids}
        return res


class ParsingDataHandler(VKParserHandler):
    def __init__(self, vk_session: vk_api.vk_api.VkApi):
        super().__init__(vk_session)
        pass

    def _check_last_time_(self):
        pass

    def parse_ids(self, ids: list):
        valid_ids = []
        users_dict = {}

        # parse main info from user page
        users_info = self.parse_user_pages(ids)
        for user_info, user_id in zip(users_info, ids):
            print(user_info)
            if not 'deactivated' in user_info and user_info['can_access_closed'] and not user_info['blacklisted']:
                valid_ids += [user_id]
            users_dict[user_id] = {'first_name': user_info['first_name'] if 'first_name' in user_info else None,
                                   'last_name': user_info['last_name'] if 'last_name' in user_info else None,
                                   'sex': user_info['sex'] if 'sex' in user_info else None,
                                   'bdate': user_info['bdate'] if 'bdate' in user_info else None,
                                   'country': user_info['country']['id'] if 'country' in user_info else None,
                                   'images': []}
            if user_info['has_photo']:
                users_dict[user_id]['images'] += [user_info['photo_max_orig']]

        # parse albums with images from user page
        users_images = self.parse_user_photos(valid_ids)
        for user_id in users_images:
            for album_id in [0, 1]:
                if users_images[user_id][album_id].ok and users_images[user_id][album_id].result['count'] > 0:
                    users_dict[user_id]['images'] += [item['sizes'][-1]['url']
                                                      for item in users_images[user_id][album_id].result['items']]

        return users_dict


if __name__ == "__main__":
    vk_session = VKAuthHandler(LOGIN, PASSWORD, bool(AUTH2CODE)).vk_session
    vk_parser = VKParserHandler(vk_session)
    # ids = [2, 293990229, 170737642]
    # print(vk_parser.parse_user_friends(ids))
    # print(vk_parser.parse_user_pages(ids))
    # print(vk_parser.parse_user_photos(ids))
    pdh = ParsingDataHandler(vk_session)
    res = pdh.parse_ids([i for i in range(1, 100)] + [170737642, 293990229])
    # res = pdh.parse_user_photos([1, 2, 170737642, 293990229])
    # res = pdh.parse_user_photos([293990229])[293990229][0].result['items'][1]['sizes'][-1]['url']
    print(res)
