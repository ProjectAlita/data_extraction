"""This module contains the class JiraFields."""
from jira import JIRA


class JiraFields:
    """
    A class to get ids of input field names associated with teams and environment where bugs/defects are registered.

    Attributes:
        fields: dict
            dictionary with the keys as names of output columns and values as field names in Jira.
    """

    def __init__(self, fields: dict):
        """
        Initialize the class with team_field and defects_environment_field parameters.
        """
        self.fields = fields

    def define_custom_fields_ids(self, jira: JIRA) -> tuple[list, dict]:
        """
        Takes input parameters for the fields names in Jira, which are related to the teams' names and defects
        environment and define their ids.
        """
        all_fields, all_fields_names = self.get_all_fields_list(jira)
        dict_custom_fields = self._create_custom_fields_dict(all_fields_names)

        custom_fields_ids = self._get_custom_fields_ids(all_fields, dict_custom_fields)

        return custom_fields_ids, dict_custom_fields

    def _get_custom_fields_ids(self, all_fields: list, dict_custom_fields: dict) -> list[str]:
        """Get ids of the input custom fields."""
        custom_fields_ids = []
        for key, value in dict_custom_fields.items():
            for field in all_fields:
                for name in value:
                    if field['name'].casefold() == name.casefold():
                        dict_custom_fields[key].append(field['id'])
                        custom_fields_ids.append(field['id'])
        return custom_fields_ids

    def _create_custom_fields_dict(self, all_fields_names: list) -> dict:
        """
        Create a dictionary with the keys as names of output columns and values as lists with field name in Jira.
        Additionally, check if the input fields exist.
        """
        input_custom_fields = [x.split(',') for x in self.fields.values() if x != '']
        input_custom_fields = [item for sublist in input_custom_fields for item in sublist]
        input_custom_fields_check = [i for i in input_custom_fields if i in all_fields_names]

        if len(input_custom_fields_check) != len(input_custom_fields):
            missing_fields = set(input_custom_fields) - set(input_custom_fields_check)
            raise ValueError(
                f"The following JIRA fields are not valid or do not exist in your JIRA instance: {', '.join(missing_fields)}. "
                f"Please check the field names on your JIRA site and verify they are spelled correctly. "
                f"You can find available fields in JIRA Administration > Issues > Custom fields."
            )

        return {key: value.split(',') for key, value in self.fields.items()}

    @staticmethod
    def get_all_fields_list(jira: JIRA) -> tuple[list, list]:
        """Get all fields of jira instance."""
        try:
            all_fields = jira.fields()
            all_fields_names = [i['name'] for i in all_fields]
            return all_fields, all_fields_names
        except Exception as e:
            error_message = str(e)
            if 'Expecting value: line 1 column 1 (char 0)' in error_message:
                raise ValueError(
                    "JIRA authentication failed - received login page instead of API response. "
                    "Please check your connection on the JIRA site and verify your credentials (username/token). "
                    "You may need to log in to JIRA again and reconnect."
                ) from e
            raise
