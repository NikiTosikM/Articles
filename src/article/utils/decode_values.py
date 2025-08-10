class DecodeValues():
    def decode_keys_and_value(article: dict[bytes, bytes]) -> dict[str, str]:
        ''' Converts keys and values in a dictionary from bits to a readable format '''
        result_decode = {key.decode("utf-8"): value.decode("utf-8") for key, value in article.items()}

        return result_decode

    def decoding_and_matching_with_fields(info: list[bytes]) -> dict[str, str]:
        ''' Decodes information to create a DisplayOnPageArticleSchema object '''
        fields = ["id", "title", "category", "views"]
        decode_data = {field: info[i].decode("utf-8") for i, field in enumerate(fields)}

        return decode_data