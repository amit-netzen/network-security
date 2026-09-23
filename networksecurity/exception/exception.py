import sys


class NetworkSecurityException(Exception):

    def __init__(self, error_message, error_details: sys):
        super().__init__(error_message)

        _, _, exc_tb = error_details.exc_info()

        self.lineno = exc_tb.tb_lineno
        self.file_name = exc_tb.tb_frame.f_code.co_filename
        self.error_message = error_message

    def __str__(self):
        return (
            f"Error occurred in Python script "
            f"[{self.file_name}] "
            f"line number [{self.lineno}] "
            f"error message [{self.error_message}]"
        )