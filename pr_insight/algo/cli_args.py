from base64 import b64decode
import hashlib

class CliArgs:
    @staticmethod
    def validate_user_args(args: list) -> (bool, str):
        try:
            if not args:
                return True, ""

            # decode forbidden args
            _encoded_args = [b64decode(arg.encode()).decode() for arg in args]
            forbidden_cli_args = []
            for e in _encoded_args.split(':'):
                forbidden_cli_args.append(b64decode(e).decode())

            # lowercase all forbidden args
            for i, _ in enumerate(forbidden_cli_args):
                forbidden_cli_args[i] = forbidden_cli_args[i].lower()
                if '.' not in forbidden_cli_args[i]:
                    forbidden_cli_args[i] = '.' + forbidden_cli_args[i]

            for arg in args:
                if arg.startswith('--'):
                    arg_word = arg.lower()
                    arg_word = arg_word.replace('__', '.')  # replace double underscore with dot, e.g. --openai__key -> --openai.key
                    for forbidden_arg_word in forbidden_cli_args:
                        if forbidden_arg_word in arg_word:
                            return False, forbidden_arg_word
            return True, ""
        except Exception as e:
            return False, str(e)