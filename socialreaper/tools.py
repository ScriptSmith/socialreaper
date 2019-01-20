import requests
import json
import csv
from os import path, makedirs
import collections


def flatten(dictionary, parent_key=False, separator='.'):
    """
    Turn a nested dictionary into a flattened dictionary

    :param dictionary: The dictionary to flatten
    :param parent_key: The string to prepend to dictionary's keys
    :param separator: The string used to separate flattened keys
    :return: A flattened dictionary
    """

    items = []
    for key, value in dictionary.items():
        new_key = str(parent_key) + separator + key if parent_key else key
        if isinstance(value, collections.MutableMapping):
            items.extend(flatten(value, new_key, separator).items())
        elif isinstance(value, list):
            for k, v in enumerate(value):
                items.extend(flatten({str(k): v}, new_key).items())
        else:
            items.append((new_key, value))
    return dict(items)


def fill_gaps(list_dicts):
    """
    Fill gaps in a list of dictionaries. Add empty keys to dictionaries in
    the list that don't contain other entries' keys

    :param list_dicts: A list of dictionaries
    :return: A list of field names, a list of dictionaries with identical keys
    """

    field_names = []  # != set bc. preserving order is better for output
    for datum in list_dicts:
        for key in datum.keys():
            if key not in field_names:
                field_names.append(key)
    for datum in list_dicts:
        for key in field_names:
            if key not in datum:
                datum[key] = ''
    return list(field_names), list_dicts


class CSV:
    def __init__(self, data, file_name='data.csv', write_headers=True,
                 append=False, key_column=None, flat=True, encoding='utf-8',
                 fill_gaps=True, field_names=None):
        self.PRIM_COL = 'primary_key'

        self.data = data
        self.file_name = file_name
        self.write_headers = write_headers
        self.append = append
        self.key_column = key_column
        self.flat = flat
        self.encoding = encoding
        self.fill_gaps = fill_gaps
        self.field_names = field_names

        if self.flat:
            self.data = [flatten(datum) for datum in self.data]

        if self.key_column:
            self.data = (self.add_key(datum) for datum in self.data)
            if self.field_names:
                self.field_names.append(self.PRIM_COL)

        self.write()

    def add_key(self, data):
        data[self.PRIM_COL] = self.key_column
        return data

    def read_fields(self):
        if path.isfile(self.file_name):
            with open(self.file_name, 'r', encoding='utf-8', newline='') as f:
                reader = csv.DictReader(f)
                return reader.fieldnames
        else:
            return None

    def read_old(self):
        if not path.isfile(self.file_name):
            return

        with open(self.file_name, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)

            data = []
            for row in reader:
                data.append(dict(row))

            data.extend(self.data)
            self.data = data

        self.field_names, self.data = fill_gaps(self.data)

    def write(self):
        if self.fill_gaps:
            self.field_names, self.data = fill_gaps(self.data)
        file_mode = 'w'

        if self.append:
            field_names = self.read_fields()
            if not field_names:
                file_mode = 'w'
            elif set(field_names) != set(self.field_names):
                self.read_old()
                file_mode = 'w'
            else:
                self.field_names = field_names
                file_mode = 'a'

        with open(self.file_name, file_mode, encoding=self.encoding, errors='ignore', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.field_names,
                                    lineterminator='\n')

            if file_mode == 'w' and self.write_headers:
                writer.writeheader()

            writer.writerows(self.data)


def to_csv(data, field_names=None, filename='data.csv',
           overwrite=True,
           write_headers=True, append=False, flat=True,
           primary_fields=None, sort_fields=True):
    """
    DEPRECATED    Write a list of dicts to a csv file

    :param data: List of dicts
    :param field_names: The list column names
    :param filename: The name of the file
    :param overwrite: Overwrite the file if exists
    :param write_headers: Write the headers to the csv file
    :param append: Write new rows if the file exists
    :param flat: Flatten the dictionary before saving
    :param primary_fields: The first columns of the csv file
    :param sort_fields: Sort the field names alphabetically
    :return: None
    """

    # Don't overwrite if not specified
    if not overwrite and path.isfile(filename):
        raise FileExistsError('The file already exists')

    # Replace file if append not specified
    write_type = 'w' if not append else 'a'

    # Flatten if flat is specified, or there are no predefined field names
    if flat or not field_names:
        data = [flatten(datum) for datum in data]

    # Fill in gaps between dicts with empty string
    if not field_names:
        field_names, data = fill_gaps(data)

    # Sort fields if specified
    if sort_fields:
        field_names.sort()

    # If there are primary fields, move the field names to the front and sort
    #  based on first field
    if primary_fields:
        for key in primary_fields[::-1]:
            field_names.insert(0, field_names.pop(field_names.index(key)))

        data = sorted(data, key=lambda k: k[field_names[0]], reverse=True)

    # Write the file
    with open(filename, write_type, encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=field_names, lineterminator='\n')
        if not append or write_headers:
            writer.writeheader()

        # Write rows containing fields in field names
        for datum in data:
            for key in list(datum.keys()):
                if key not in field_names:
                    del datum[key]
                elif type(datum[key]) is str:
                    datum[key] = datum[key].strip()

                datum[key] = str(datum[key])

            writer.writerow(datum)


def to_json(data, filename='data.json', indent=4):
    """
    Write an object to a json file

    :param data: The object
    :param filename: The name of the file
    :param indent: The indentation of the file
    :return: None
    """

    with open(filename, 'w') as f:
        f.write(json.dumps(data, indent=indent))


def save_file(filename, source, folder="Downloads"):
    """
    Download and save a file at path

    :param filename: The name of the file
    :param source: The location of the resource online
    :param folder: The directory the file will be saved in
    :return: None
    """

    r = requests.get(source, stream=True)
    if r.status_code == 200:
        if not path.isdir(folder):
            makedirs(folder, exist_ok=True)
        with open("%s/%s" % (folder, filename), 'wb') as f:
            for chunk in r:
                f.write(chunk)


def iter_print(iterable):
    for item in iterable:
        print(item)
