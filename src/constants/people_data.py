"""
Family Tree People Dictionary

This file contains a comprehensive dictionary of all people in the family tree.
Generated automatically by scan_people.py

Structure:
  PEOPLE_BY_UUID: Dict[str, Dict]
    - Key: unique_identifier (UUID string)
    - Value: Dictionary containing:
      - unique_identifier: UUID of the person
      - person_name: Full name from me.json
      - location: Location from me.json
      - folder_name: Name of the folder on disk
      - folder_path: Absolute path to the folder

  NON_CONFORMING_FOLDERS: List[str]
    - List of folder names that do not follow the 2-9 word naming pattern
    - Pattern check: folder_name.split(" ") should have 2-9 elements
"""

from typing import Dict, List

# Dictionary of all people indexed by UUID
PEOPLE_BY_UUID: Dict[str, Dict[str, str]] = {
    "d4966e3e-7668-4362-8e1b-04b7635a141c": {
        "unique_identifier": "d4966e3e-7668-4362-8e1b-04b7635a141c",
        "person_name": "(nieznane) (nieznane) zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Mankin\\(nieznane) (nieznane) zd. (nieznane)",
        "folder_name": "(nieznane) (nieznane) zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\(nieznane) (nieznane) zd. (nieznane)"
    },
    "ffd96a4b-1f37-48b0-96f1-058b02827753": {
        "unique_identifier": "ffd96a4b-1f37-48b0-96f1-058b02827753",
        "person_name": "(nieznane) Kominek;Kuminek (1)",
        "location": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Kominek;Kuminek (1)",
        "folder_name": "(nieznane) Kominek;Kuminek (1)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Kominek;Kuminek (1)"
    },
    "919c1fbd-1f38-42a9-8540-b40529bc2ea7": {
        "unique_identifier": "919c1fbd-1f38-42a9-8540-b40529bc2ea7",
        "person_name": "(nieznane) Kominek;Kuminek (2)",
        "location": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Kominek;Kuminek (2)",
        "folder_name": "(nieznane) Kominek;Kuminek (2)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Kominek;Kuminek (2)"
    },
    "1836c350-5d63-4e9a-aa39-2f94bca61140": {
        "unique_identifier": "1836c350-5d63-4e9a-aa39-2f94bca61140",
        "person_name": "(nieznane) Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Manke",
        "folder_name": "(nieznane) Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Manke"
    },
    "7f9fecaf-ebc8-4b07-9afd-3d612aeef2c3": {
        "unique_identifier": "7f9fecaf-ebc8-4b07-9afd-3d612aeef2c3",
        "person_name": "(nieznane) Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Mankin",
        "folder_name": "(nieznane) Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Mankin"
    },
    "a9e5773c-2fc7-4003-a844-55bce8ad2bf0": {
        "unique_identifier": "a9e5773c-2fc7-4003-a844-55bce8ad2bf0",
        "person_name": "(nieznane) Pełnikowski",
        "location": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Pełnikowski",
        "folder_name": "(nieznane) Pełnikowski",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\(nieznane) Pełnikowski"
    },
    "f3a7af9d-d0ea-4da3-abac-6cfcc6cf243e": {
        "unique_identifier": "f3a7af9d-d0ea-4da3-abac-6cfcc6cf243e",
        "person_name": "Adam (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Adam (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Adam (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Adam (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "d4dd0d33-cc90-47fb-ab0f-212c72af1574": {
        "unique_identifier": "d4dd0d33-cc90-47fb-ab0f-212c72af1574",
        "person_name": "Adam Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Adam Mankin",
        "folder_name": "Adam Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Adam Mankin"
    },
    "10d3cf2f-b95a-4400-8586-60d097a715c2": {
        "unique_identifier": "10d3cf2f-b95a-4400-8586-60d097a715c2",
        "person_name": "Agnieszka Karpińska zd. Ziemińska",
        "location": "C:\\Sorted tree\\People\\Mankin\\Agnieszka Karpińska zd. Ziemińska",
        "folder_name": "Agnieszka Karpińska zd. Ziemińska",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Agnieszka Karpińska zd. Ziemińska"
    },
    "70fc6d95-1cf6-4d2a-a8aa-1fcd7c2a6f70": {
        "unique_identifier": "70fc6d95-1cf6-4d2a-a8aa-1fcd7c2a6f70",
        "person_name": "Agnieszka Łuciuk zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Mankin\\Agnieszka Łuciuk zd. (nieznane) - matka Danuta Pastryk",
        "folder_name": "Agnieszka Łuciuk zd. (nieznane) - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Agnieszka Łuciuk zd. (nieznane) - matka Danuta Pastryk"
    },
    "9d2026c5-6764-45bf-a7d3-19e4440ea579": {
        "unique_identifier": "9d2026c5-6764-45bf-a7d3-19e4440ea579",
        "person_name": "Andrzej Ziemiński",
        "location": "C:\\Sorted tree\\People\\Mankin\\Andrzej Ziemiński",
        "folder_name": "Andrzej Ziemiński",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Andrzej Ziemiński"
    },
    "64afd77a-b075-40ad-a5bd-3d0299b78439": {
        "unique_identifier": "64afd77a-b075-40ad-a5bd-3d0299b78439",
        "person_name": "Aneta Stefaniszyn zd. Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Aneta Stefaniszyn zd. Pastryk",
        "folder_name": "Aneta Stefaniszyn zd. Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Aneta Stefaniszyn zd. Pastryk"
    },
    "c237ee24-ff67-4260-91b4-6390d8ce0dc5": {
        "unique_identifier": "c237ee24-ff67-4260-91b4-6390d8ce0dc5",
        "person_name": "Aneta Ziemińska zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Mankin\\Aneta Ziemińska zd. (nieznane)",
        "folder_name": "Aneta Ziemińska zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Aneta Ziemińska zd. (nieznane)"
    },
    "b16ec0a6-8e2b-42b9-84cb-310a1701451a": {
        "unique_identifier": "b16ec0a6-8e2b-42b9-84cb-310a1701451a",
        "person_name": "Anna Mankin;Manke zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Mankin\\Anna Mankin;Manke zd. (nieznane)",
        "folder_name": "Anna Mankin;Manke zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Anna Mankin;Manke zd. (nieznane)"
    },
    "ebe5f849-3fb6-49d7-8767-f72f4ab80b57": {
        "unique_identifier": "ebe5f849-3fb6-49d7-8767-f72f4ab80b57",
        "person_name": "Arkadiusz Olejnik",
        "location": "C:\\Sorted tree\\People\\Mankin\\Arkadiusz Olejnik",
        "folder_name": "Arkadiusz Olejnik",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Arkadiusz Olejnik"
    },
    "6e554e4a-810d-454f-a753-7ba4ef32cd5f": {
        "unique_identifier": "6e554e4a-810d-454f-a753-7ba4ef32cd5f",
        "person_name": "Artur (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Artur (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Artur (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Artur (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "f569ab71-bbb5-41af-9b86-da8ea89cd5d1": {
        "unique_identifier": "f569ab71-bbb5-41af-9b86-da8ea89cd5d1",
        "person_name": "Bartek Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Bartek Manke",
        "folder_name": "Bartek Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Bartek Manke"
    },
    "50a83e48-412c-46c1-931c-444496e84b1d": {
        "unique_identifier": "50a83e48-412c-46c1-931c-444496e84b1d",
        "person_name": "Bolesław Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Bolesław Manke",
        "folder_name": "Bolesław Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Bolesław Manke"
    },
    "36ce6af4-434b-4a2d-adfd-8e24cf218e4e": {
        "unique_identifier": "36ce6af4-434b-4a2d-adfd-8e24cf218e4e",
        "person_name": "Bożena Galaszewska zd. Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Bożena Galaszewska zd. Mankin",
        "folder_name": "Bożena Galaszewska zd. Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Bożena Galaszewska zd. Mankin"
    },
    "7227bf77-9dd3-4865-a285-35acd5823c12": {
        "unique_identifier": "7227bf77-9dd3-4865-a285-35acd5823c12",
        "person_name": "Bożena Ziemińska zd. Pełnikowska",
        "location": "C:\\Sorted tree\\People\\Mankin\\Bożena Ziemińska zd. Pełnikowska",
        "folder_name": "Bożena Ziemińska zd. Pełnikowska",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Bożena Ziemińska zd. Pełnikowska"
    },
    "401468ec-649f-41c4-923c-1eb353751f9d": {
        "unique_identifier": "401468ec-649f-41c4-923c-1eb353751f9d",
        "person_name": "Bruno Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Bruno Pastryk",
        "folder_name": "Bruno Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Bruno Pastryk"
    },
    "7e031a74-2333-40b6-922d-09a3fa4b745b": {
        "unique_identifier": "7e031a74-2333-40b6-922d-09a3fa4b745b",
        "person_name": "Danuta (nieznane) zd. Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Danuta (nieznane) zd. Pastryk",
        "folder_name": "Danuta (nieznane) zd. Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Danuta (nieznane) zd. Pastryk"
    },
    "f571a70f-ca22-49f4-b365-4a7637db69e7": {
        "unique_identifier": "f571a70f-ca22-49f4-b365-4a7637db69e7",
        "person_name": "Dominik (nieznane)vPastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Dominik (nieznane)vPastryk",
        "folder_name": "Dominik (nieznane)vPastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Dominik (nieznane)vPastryk"
    },
    "f4229e03-7f06-48c0-af50-bf180861a0c7": {
        "unique_identifier": "f4229e03-7f06-48c0-af50-bf180861a0c7",
        "person_name": "Ewa (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Ewa (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Ewa (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Ewa (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "2da4a425-e159-4c5d-bbff-cd2e54bedd5c": {
        "unique_identifier": "2da4a425-e159-4c5d-bbff-cd2e54bedd5c",
        "person_name": "Franciszek Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Franciszek Manke",
        "folder_name": "Franciszek Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Franciszek Manke"
    },
    "8f5ee906-e291-490b-8940-21a4061427b7": {
        "unique_identifier": "8f5ee906-e291-490b-8940-21a4061427b7",
        "person_name": "Halina Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Halina Mankin",
        "folder_name": "Halina Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Halina Mankin"
    },
    "fbebe92d-f8cb-4e43-925f-72cc8ab2a100": {
        "unique_identifier": "fbebe92d-f8cb-4e43-925f-72cc8ab2a100",
        "person_name": "Ignacy Kominek;Kuminek",
        "location": "C:\\Sorted tree\\People\\Mankin\\Ignacy Kominek;Kuminek",
        "folder_name": "Ignacy Kominek;Kuminek",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Ignacy Kominek;Kuminek"
    },
    "4572258d-7cb9-4f0b-9b92-9583e7cb746a": {
        "unique_identifier": "4572258d-7cb9-4f0b-9b92-9583e7cb746a",
        "person_name": "Ilona Legut zd. Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Ilona Legut zd. Pastryk",
        "folder_name": "Ilona Legut zd. Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Ilona Legut zd. Pastryk"
    },
    "21d07afb-9f82-4df1-b66a-0d60d803c31e": {
        "unique_identifier": "21d07afb-9f82-4df1-b66a-0d60d803c31e",
        "person_name": "Irena Pastryk zd. Mankin;Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Irena Pastryk zd. Mankin;Manke",
        "folder_name": "Irena Pastryk zd. Mankin;Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Irena Pastryk zd. Mankin;Manke"
    },
    "bf978ac6-8a07-4fc8-90ba-f2dd14a327d1": {
        "unique_identifier": "bf978ac6-8a07-4fc8-90ba-f2dd14a327d1",
        "person_name": "Ireneusz Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Ireneusz Pastryk",
        "folder_name": "Ireneusz Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Ireneusz Pastryk"
    },
    "43c39566-7f69-4f85-bdc0-81013e99b958": {
        "unique_identifier": "43c39566-7f69-4f85-bdc0-81013e99b958",
        "person_name": "Jacek (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Jacek (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Jacek (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Jacek (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "885744d6-b812-4ea4-8bfe-f3a0f6c797ac": {
        "unique_identifier": "885744d6-b812-4ea4-8bfe-f3a0f6c797ac",
        "person_name": "Jadwiga Manke zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Mankin\\Jadwiga Manke zd. (nieznane)",
        "folder_name": "Jadwiga Manke zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Jadwiga Manke zd. (nieznane)"
    },
    "cb30c257-65f9-400d-ac1d-782bd1405efe": {
        "unique_identifier": "cb30c257-65f9-400d-ac1d-782bd1405efe",
        "person_name": "Jerzy Galaszewski",
        "location": "C:\\Sorted tree\\People\\Mankin\\Jerzy Galaszewski",
        "folder_name": "Jerzy Galaszewski",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Jerzy Galaszewski"
    },
    "3370f768-e81a-4b57-9cc5-d3a481a25776": {
        "unique_identifier": "3370f768-e81a-4b57-9cc5-d3a481a25776",
        "person_name": "Joanna Manke zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Mankin\\Joanna Manke zd. (nieznane)",
        "folder_name": "Joanna Manke zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Joanna Manke zd. (nieznane)"
    },
    "866421a8-4132-45e9-b2a0-ea5e78cf19df": {
        "unique_identifier": "866421a8-4132-45e9-b2a0-ea5e78cf19df",
        "person_name": "Julian Mankin;Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Julian Mankin;Manke",
        "folder_name": "Julian Mankin;Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Julian Mankin;Manke"
    },
    "4f06c658-41cb-40a7-8057-996c3e50e3f0": {
        "unique_identifier": "4f06c658-41cb-40a7-8057-996c3e50e3f0",
        "person_name": "Jurek Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Jurek Mankin",
        "folder_name": "Jurek Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Jurek Mankin"
    },
    "094f27c9-82a9-4ea4-98f0-df6b58208189": {
        "unique_identifier": "094f27c9-82a9-4ea4-98f0-df6b58208189",
        "person_name": "Józef Pełnikowski",
        "location": "C:\\Sorted tree\\People\\Mankin\\Józef Pełnikowski",
        "folder_name": "Józef Pełnikowski",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Józef Pełnikowski"
    },
    "4de3a6d4-de95-4e37-87f1-8affce011c38": {
        "unique_identifier": "4de3a6d4-de95-4e37-87f1-8affce011c38",
        "person_name": "Katarzyna Szafran zd. Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Katarzyna Szafran zd. Mankin",
        "folder_name": "Katarzyna Szafran zd. Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Katarzyna Szafran zd. Mankin"
    },
    "96e871b7-4d55-42c8-8a3d-85de0eeb50ee": {
        "unique_identifier": "96e871b7-4d55-42c8-8a3d-85de0eeb50ee",
        "person_name": "Kazimierz Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Kazimierz Mankin",
        "folder_name": "Kazimierz Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Kazimierz Mankin"
    },
    "653fea87-4801-436c-b55f-095b8a3cd0ea": {
        "unique_identifier": "653fea87-4801-436c-b55f-095b8a3cd0ea",
        "person_name": "Konrad Galaszewski",
        "location": "C:\\Sorted tree\\People\\Mankin\\Konrad Galaszewski",
        "folder_name": "Konrad Galaszewski",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Konrad Galaszewski"
    },
    "2876cc84-a5e9-4630-9338-bfc9cf2e7e37": {
        "unique_identifier": "2876cc84-a5e9-4630-9338-bfc9cf2e7e37",
        "person_name": "Leszek Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Leszek Mankin",
        "folder_name": "Leszek Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Leszek Mankin"
    },
    "59ffc022-3ccb-470a-b4ca-4bdb3b56ca2a": {
        "unique_identifier": "59ffc022-3ccb-470a-b4ca-4bdb3b56ca2a",
        "person_name": "Lucyna Mankin zd. Salomon;Salamon",
        "location": "C:\\Sorted tree\\People\\Mankin\\Lucyna Mankin zd. Salomon;Salamon",
        "folder_name": "Lucyna Mankin zd. Salomon;Salamon",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Lucyna Mankin zd. Salomon;Salamon"
    },
    "17357412-b9a7-4870-8d99-f8edcf79e475": {
        "unique_identifier": "17357412-b9a7-4870-8d99-f8edcf79e475",
        "person_name": "Magdalena Pasierb-Skoczylas zd. (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Magdalena Pasierb-Skoczylas zd. (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Magdalena Pasierb-Skoczylas zd. (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Magdalena Pasierb-Skoczylas zd. (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "457efbe1-ce93-4098-b715-9043f0a200fa": {
        "unique_identifier": "457efbe1-ce93-4098-b715-9043f0a200fa",
        "person_name": "Marcin Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Marcin Manke",
        "folder_name": "Marcin Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Marcin Manke"
    },
    "0efebdda-d0d0-4955-b8cd-cc9680c8122c": {
        "unique_identifier": "0efebdda-d0d0-4955-b8cd-cc9680c8122c",
        "person_name": "Marek (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Marek (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Marek (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Marek (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "2d7879f8-f335-4260-9fb5-0765933282fb": {
        "unique_identifier": "2d7879f8-f335-4260-9fb5-0765933282fb",
        "person_name": "Marianna Kominek;Kuminek zd. Mikołajczyk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Marianna Kominek;Kuminek zd. Mikołajczyk",
        "folder_name": "Marianna Kominek;Kuminek zd. Mikołajczyk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Marianna Kominek;Kuminek zd. Mikołajczyk"
    },
    "4f421011-e8d7-4598-a9c2-c5af8c05ede2": {
        "unique_identifier": "4f421011-e8d7-4598-a9c2-c5af8c05ede2",
        "person_name": "Mariusz Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Mariusz Pastryk",
        "folder_name": "Mariusz Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Mariusz Pastryk"
    },
    "f3bea774-0fa7-49d5-84c5-8bc79f478d31": {
        "unique_identifier": "f3bea774-0fa7-49d5-84c5-8bc79f478d31",
        "person_name": "Marta (nieznane) zd. (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Marta (nieznane) zd. (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Marta (nieznane) zd. (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Marta (nieznane) zd. (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "d552cc3a-14db-4476-9bdc-f9452e625ce7": {
        "unique_identifier": "d552cc3a-14db-4476-9bdc-f9452e625ce7",
        "person_name": "Michał (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Michał (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Michał (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Michał (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "e5590928-8f06-4194-b60f-f6e221495354": {
        "unique_identifier": "e5590928-8f06-4194-b60f-f6e221495354",
        "person_name": "Michał Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Michał Manke",
        "folder_name": "Michał Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Michał Manke"
    },
    "08b1e25c-0220-47ee-9b70-dc56ddb7a7cd": {
        "unique_identifier": "08b1e25c-0220-47ee-9b70-dc56ddb7a7cd",
        "person_name": "Nikodem Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Nikodem Pastryk",
        "folder_name": "Nikodem Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Nikodem Pastryk"
    },
    "9c485b68-61ad-4d56-967b-72e0d81dcf57": {
        "unique_identifier": "9c485b68-61ad-4d56-967b-72e0d81dcf57",
        "person_name": "Paweł Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Paweł Manke",
        "folder_name": "Paweł Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Paweł Manke"
    },
    "a074a0fe-d90c-490f-9162-4aad1bb54a8e": {
        "unique_identifier": "a074a0fe-d90c-490f-9162-4aad1bb54a8e",
        "person_name": "Przemysław (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Przemysław (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Przemysław (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Przemysław (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "4480090d-d474-460b-918e-a76e4d015ce5": {
        "unique_identifier": "4480090d-d474-460b-918e-a76e4d015ce5",
        "person_name": "Robert Ziemiński",
        "location": "C:\\Sorted tree\\People\\Mankin\\Robert Ziemiński",
        "folder_name": "Robert Ziemiński",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Robert Ziemiński"
    },
    "d97da593-9e38-48fd-b6c3-1449a5851245": {
        "unique_identifier": "d97da593-9e38-48fd-b6c3-1449a5851245",
        "person_name": "Roman Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Roman Mankin",
        "folder_name": "Roman Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Roman Mankin"
    },
    "d806123e-55dd-442c-a09c-884977eed14a": {
        "unique_identifier": "d806123e-55dd-442c-a09c-884977eed14a",
        "person_name": "Ryszard Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Ryszard Manke",
        "folder_name": "Ryszard Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Ryszard Manke"
    },
    "44133991-9ca8-4b90-a4c2-7180e4a5a675": {
        "unique_identifier": "44133991-9ca8-4b90-a4c2-7180e4a5a675",
        "person_name": "Ryszard Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Ryszard Mankin",
        "folder_name": "Ryszard Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Ryszard Mankin"
    },
    "58dd28f4-aaaf-40e5-b2b6-2124fac1ee65": {
        "unique_identifier": "58dd28f4-aaaf-40e5-b2b6-2124fac1ee65",
        "person_name": "Ryszard Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Ryszard Pastryk",
        "folder_name": "Ryszard Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Ryszard Pastryk"
    },
    "6e2a711f-74a3-47fd-8c38-3b0244774e00": {
        "unique_identifier": "6e2a711f-74a3-47fd-8c38-3b0244774e00",
        "person_name": "Ryszard Ziemiński",
        "location": "C:\\Sorted tree\\People\\Mankin\\Ryszard Ziemiński",
        "folder_name": "Ryszard Ziemiński",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Ryszard Ziemiński"
    },
    "4d73de33-0fb4-4ef4-b333-0e4ddaf0148e": {
        "unique_identifier": "4d73de33-0fb4-4ef4-b333-0e4ddaf0148e",
        "person_name": "Stanisław Mankin;Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Stanisław Mankin;Manke",
        "folder_name": "Stanisław Mankin;Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Stanisław Mankin;Manke"
    },
    "9f76a157-df82-44a8-a84f-85a8c57e878f": {
        "unique_identifier": "9f76a157-df82-44a8-a84f-85a8c57e878f",
        "person_name": "Stanisław Pastryk (1)",
        "location": "C:\\Sorted tree\\People\\Mankin\\Stanisław Pastryk (1)",
        "folder_name": "Stanisław Pastryk (1)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Stanisław Pastryk (1)"
    },
    "ba9ae24a-35a1-4d9e-b6c3-758afb6cfaf3": {
        "unique_identifier": "ba9ae24a-35a1-4d9e-b6c3-758afb6cfaf3",
        "person_name": "Stanisław Pastryk (2)",
        "location": "C:\\Sorted tree\\People\\Mankin\\Stanisław Pastryk (2)",
        "folder_name": "Stanisław Pastryk (2)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Stanisław Pastryk (2)"
    },
    "6bb383ca-d470-49b5-924a-c8b0f528cf65": {
        "unique_identifier": "6bb383ca-d470-49b5-924a-c8b0f528cf65",
        "person_name": "Stanisława Mankin;Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Stanisława Mankin;Manke",
        "folder_name": "Stanisława Mankin;Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Stanisława Mankin;Manke"
    },
    "3df8cdf6-2d88-4d49-9d58-dfb2a97499eb": {
        "unique_identifier": "3df8cdf6-2d88-4d49-9d58-dfb2a97499eb",
        "person_name": "Sylwester (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Sylwester (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Sylwester (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Sylwester (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "b5c666fd-2623-4e11-a93b-d5fe21994702": {
        "unique_identifier": "b5c666fd-2623-4e11-a93b-d5fe21994702",
        "person_name": "Sylwia Maria Omiotek zd. (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Sylwia Maria Omiotek zd. (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Sylwia Maria Omiotek zd. (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Sylwia Maria Omiotek zd. (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "3935cb2d-84e5-443c-8d08-ca95dcd68339": {
        "unique_identifier": "3935cb2d-84e5-443c-8d08-ca95dcd68339",
        "person_name": "Sylwia Misiak zd. Galaszewska",
        "location": "C:\\Sorted tree\\People\\Mankin\\Sylwia Misiak zd. Galaszewska",
        "folder_name": "Sylwia Misiak zd. Galaszewska",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Sylwia Misiak zd. Galaszewska"
    },
    "7a5cd043-3fc2-4ae6-81b6-11f5ed3e71fe": {
        "unique_identifier": "7a5cd043-3fc2-4ae6-81b6-11f5ed3e71fe",
        "person_name": "Tomasz Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Tomasz Mankin",
        "folder_name": "Tomasz Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Tomasz Mankin"
    },
    "d6d9850a-15d7-4c5f-bb92-e487ec772974": {
        "unique_identifier": "d6d9850a-15d7-4c5f-bb92-e487ec772974",
        "person_name": "Tomasz Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Tomasz Pastryk",
        "folder_name": "Tomasz Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Tomasz Pastryk"
    },
    "7a1c2e08-953c-4134-8c4d-01bff7658ebf": {
        "unique_identifier": "7a1c2e08-953c-4134-8c4d-01bff7658ebf",
        "person_name": "Wacława Pełnikowska zd. Mankin;Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Wacława Pełnikowska zd. Mankin;Manke",
        "folder_name": "Wacława Pełnikowska zd. Mankin;Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Wacława Pełnikowska zd. Mankin;Manke"
    },
    "e82218f2-3cf8-4738-a10b-28120845d046": {
        "unique_identifier": "e82218f2-3cf8-4738-a10b-28120845d046",
        "person_name": "Waldemar Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Waldemar Manke",
        "folder_name": "Waldemar Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Waldemar Manke"
    },
    "c93e5e81-d99a-459e-a127-a188d1316880": {
        "unique_identifier": "c93e5e81-d99a-459e-a127-a188d1316880",
        "person_name": "Wanda Manke zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Mankin\\Wanda Manke zd. (nieznane)",
        "folder_name": "Wanda Manke zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Wanda Manke zd. (nieznane)"
    },
    "100b5a12-2ad3-48a6-a450-f9b2ac0c8b4a": {
        "unique_identifier": "100b5a12-2ad3-48a6-a450-f9b2ac0c8b4a",
        "person_name": "Wojciech (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Wojciech (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Wojciech (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Wojciech (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "95c31e48-9525-4aa1-97a2-fb37e2aa234c": {
        "unique_identifier": "95c31e48-9525-4aa1-97a2-fb37e2aa234c",
        "person_name": "Władysława Mankin;Manke zd. Kuminek;Kominek",
        "location": "C:\\Sorted tree\\People\\Mankin\\Władysława Mankin;Manke zd. Kuminek;Kominek",
        "folder_name": "Władysława Mankin;Manke zd. Kuminek;Kominek",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Władysława Mankin;Manke zd. Kuminek;Kominek"
    },
    "62b0318f-e825-4145-88e8-eab3baea082e": {
        "unique_identifier": "62b0318f-e825-4145-88e8-eab3baea082e",
        "person_name": "Zbigniew Mankin",
        "location": "C:\\Sorted tree\\People\\Mankin\\Zbigniew Mankin",
        "folder_name": "Zbigniew Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Zbigniew Mankin"
    },
    "8304b1d7-6dc6-4233-8ecf-d014d85576f3": {
        "unique_identifier": "8304b1d7-6dc6-4233-8ecf-d014d85576f3",
        "person_name": "Łukasz (nieznane)vPastryk - matka Danuta Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Łukasz (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_name": "Łukasz (nieznane)vPastryk - matka Danuta Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Łukasz (nieznane)vPastryk - matka Danuta Pastryk"
    },
    "7959135d-2935-4560-bd1e-8c09c3f19123": {
        "unique_identifier": "7959135d-2935-4560-bd1e-8c09c3f19123",
        "person_name": "Łukasz Manke",
        "location": "C:\\Sorted tree\\People\\Mankin\\Łukasz Manke",
        "folder_name": "Łukasz Manke",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Łukasz Manke"
    },
    "f5cc1dd2-c468-4f1c-921d-045963de9fe7": {
        "unique_identifier": "f5cc1dd2-c468-4f1c-921d-045963de9fe7",
        "person_name": "Łukasz Pastryk",
        "location": "C:\\Sorted tree\\People\\Mankin\\Łukasz Pastryk",
        "folder_name": "Łukasz Pastryk",
        "folder_path": "C:\\Sorted tree\\People\\Mankin\\Łukasz Pastryk"
    },
    "bd2e97a8-e0eb-4091-9720-c1470e7ec516": {
        "unique_identifier": "bd2e97a8-e0eb-4091-9720-c1470e7ec516",
        "person_name": "(nieznane) (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) (nieznane)",
        "folder_name": "(nieznane) (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) (nieznane)"
    },
    "457d9eff-a501-439f-9d40-f0f5b5e25a71": {
        "unique_identifier": "457d9eff-a501-439f-9d40-f0f5b5e25a71",
        "person_name": "(nieznane) (nieznane) zd. (nieznane) (1)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) (nieznane) zd. (nieznane) (1)",
        "folder_name": "(nieznane) (nieznane) zd. (nieznane) (1)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) (nieznane) zd. (nieznane) (1)"
    },
    "750d8577-1c65-4fcc-aae0-c1f4544b7f96": {
        "unique_identifier": "750d8577-1c65-4fcc-aae0-c1f4544b7f96",
        "person_name": "(nieznane) (nieznane) zd. (nieznane) (2)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) (nieznane) zd. (nieznane) (2)",
        "folder_name": "(nieznane) (nieznane) zd. (nieznane) (2)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) (nieznane) zd. (nieznane) (2)"
    },
    "6de89626-fe67-4f39-9946-fd200d23cd7b": {
        "unique_identifier": "6de89626-fe67-4f39-9946-fd200d23cd7b",
        "person_name": "(nieznane) Kowalska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Kowalska",
        "folder_name": "(nieznane) Kowalska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Kowalska"
    },
    "fc9343fa-9045-4ee7-ac55-437f2a6ff289": {
        "unique_identifier": "fc9343fa-9045-4ee7-ac55-437f2a6ff289",
        "person_name": "(nieznane) Kowalski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Kowalski",
        "folder_name": "(nieznane) Kowalski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Kowalski"
    },
    "17a50216-3301-4b63-8c70-9eb032318b8b": {
        "unique_identifier": "17a50216-3301-4b63-8c70-9eb032318b8b",
        "person_name": "(nieznane) Lewandowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Lewandowski",
        "folder_name": "(nieznane) Lewandowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Lewandowski"
    },
    "733f200b-321d-4974-8cda-8c266e47f9fa": {
        "unique_identifier": "733f200b-321d-4974-8cda-8c266e47f9fa",
        "person_name": "(nieznane) Radzińska zd. Śliwińska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Radzińska zd. Śliwińska",
        "folder_name": "(nieznane) Radzińska zd. Śliwińska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Radzińska zd. Śliwińska"
    },
    "7b0b73e2-c018-4968-a0f5-a5aa6c32a91e": {
        "unique_identifier": "7b0b73e2-c018-4968-a0f5-a5aa6c32a91e",
        "person_name": "(nieznane) Sadowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Sadowski",
        "folder_name": "(nieznane) Sadowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Sadowski"
    },
    "ced9798b-2e90-4074-a605-841993afa1c3": {
        "unique_identifier": "ced9798b-2e90-4074-a605-841993afa1c3",
        "person_name": "(nieznane) Łodzkiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Łodzkiewicz",
        "folder_name": "(nieznane) Łodzkiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Łodzkiewicz"
    },
    "bfe57281-cb4d-4617-8119-76af0af8606c": {
        "unique_identifier": "bfe57281-cb4d-4617-8119-76af0af8606c",
        "person_name": "(nieznane) Łodzkiewicz zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Łodzkiewicz zd. (nieznane)",
        "folder_name": "(nieznane) Łodzkiewicz zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\(nieznane) Łodzkiewicz zd. (nieznane)"
    },
    "ffafc705-0484-4062-89d8-6aa76affd8ed": {
        "unique_identifier": "ffafc705-0484-4062-89d8-6aa76affd8ed",
        "person_name": "Adam Rutowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Adam Rutowski",
        "folder_name": "Adam Rutowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Adam Rutowski"
    },
    "db077531-0373-4170-b639-4c5ec485c02f": {
        "unique_identifier": "db077531-0373-4170-b639-4c5ec485c02f",
        "person_name": "Adrian Kowalski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Adrian Kowalski",
        "folder_name": "Adrian Kowalski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Adrian Kowalski"
    },
    "f5146a7c-4435-4d3f-b01d-871dd1688fde": {
        "unique_identifier": "f5146a7c-4435-4d3f-b01d-871dd1688fde",
        "person_name": "Agata (nieznane) zd. Olewnik",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Agata (nieznane) zd. Olewnik",
        "folder_name": "Agata (nieznane) zd. Olewnik",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Agata (nieznane) zd. Olewnik"
    },
    "7b7bc265-418a-4333-aedc-b66e21ac31fb": {
        "unique_identifier": "7b7bc265-418a-4333-aedc-b66e21ac31fb",
        "person_name": "Agata Łodzkiewicz zd. Krzeszewska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Agata Łodzkiewicz zd. Krzeszewska",
        "folder_name": "Agata Łodzkiewicz zd. Krzeszewska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Agata Łodzkiewicz zd. Krzeszewska"
    },
    "f5d28c02-34b8-428c-8c98-a41e9f976171": {
        "unique_identifier": "f5d28c02-34b8-428c-8c98-a41e9f976171",
        "person_name": "Aleksander Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Aleksander Matynka",
        "folder_name": "Aleksander Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Aleksander Matynka"
    },
    "45070c29-219f-4a32-a1e5-32ee1f15c477": {
        "unique_identifier": "45070c29-219f-4a32-a1e5-32ee1f15c477",
        "person_name": "Alicja Jesionowska zd. Olewnik",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Alicja Jesionowska zd. Olewnik",
        "folder_name": "Alicja Jesionowska zd. Olewnik",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Alicja Jesionowska zd. Olewnik"
    },
    "9bddde26-4975-4a30-aa67-629dc742e869": {
        "unique_identifier": "9bddde26-4975-4a30-aa67-629dc742e869",
        "person_name": "Alicja Sobierajska zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Alicja Sobierajska zd. (nieznane)",
        "folder_name": "Alicja Sobierajska zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Alicja Sobierajska zd. (nieznane)"
    },
    "1ff5ca52-8108-4e17-aafa-2d48004af20a": {
        "unique_identifier": "1ff5ca52-8108-4e17-aafa-2d48004af20a",
        "person_name": "Anastazja Śpiewakowska zd. Czajkowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Anastazja Śpiewakowska zd. Czajkowska",
        "folder_name": "Anastazja Śpiewakowska zd. Czajkowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Anastazja Śpiewakowska zd. Czajkowska"
    },
    "e05f0c2b-5f7e-4971-ada7-c02f88524d92": {
        "unique_identifier": "e05f0c2b-5f7e-4971-ada7-c02f88524d92",
        "person_name": "Andrzej Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Andrzej Krankiewicz",
        "folder_name": "Andrzej Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Andrzej Krankiewicz"
    },
    "39dfe9be-6c30-454e-9765-b4ef5c3bebb9": {
        "unique_identifier": "39dfe9be-6c30-454e-9765-b4ef5c3bebb9",
        "person_name": "Anna (nieznane) zd. Czajkowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Anna (nieznane) zd. Czajkowska",
        "folder_name": "Anna (nieznane) zd. Czajkowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Anna (nieznane) zd. Czajkowska"
    },
    "33174150-a4de-4a81-aec5-250ff40de03d": {
        "unique_identifier": "33174150-a4de-4a81-aec5-250ff40de03d",
        "person_name": "Anna Lewandowska zd. Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Anna Lewandowska zd. Matynka",
        "folder_name": "Anna Lewandowska zd. Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Anna Lewandowska zd. Matynka"
    },
    "1c032ff6-97c4-4e62-bb31-edecafaf0b10": {
        "unique_identifier": "1c032ff6-97c4-4e62-bb31-edecafaf0b10",
        "person_name": "Anna Pietrzak zd. Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Anna Pietrzak zd. Matynka",
        "folder_name": "Anna Pietrzak zd. Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Anna Pietrzak zd. Matynka"
    },
    "ccd51191-c361-486c-bd1f-aa601a4b2ab2": {
        "unique_identifier": "ccd51191-c361-486c-bd1f-aa601a4b2ab2",
        "person_name": "Antoni Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Antoni Krankiewicz",
        "folder_name": "Antoni Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Antoni Krankiewicz"
    },
    "de0fd441-ca1a-4cd5-bc9d-4fb30723eb09": {
        "unique_identifier": "de0fd441-ca1a-4cd5-bc9d-4fb30723eb09",
        "person_name": "Apolonia Śliwińska zd. Lemańska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Apolonia Śliwińska zd. Lemańska",
        "folder_name": "Apolonia Śliwińska zd. Lemańska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Apolonia Śliwińska zd. Lemańska"
    },
    "2d22050c-4e69-43a7-9e79-64f6949173b3": {
        "unique_identifier": "2d22050c-4e69-43a7-9e79-64f6949173b3",
        "person_name": "Artur Sobierajski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Artur Sobierajski",
        "folder_name": "Artur Sobierajski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Artur Sobierajski"
    },
    "4c8d39af-f386-4b95-8e30-5baf0f2d0ee0": {
        "unique_identifier": "4c8d39af-f386-4b95-8e30-5baf0f2d0ee0",
        "person_name": "Bogdan Kowalski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Bogdan Kowalski",
        "folder_name": "Bogdan Kowalski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Bogdan Kowalski"
    },
    "ff31c528-822f-4736-8afd-1cb4116927b6": {
        "unique_identifier": "ff31c528-822f-4736-8afd-1cb4116927b6",
        "person_name": "Bogdan Olewnik",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Bogdan Olewnik",
        "folder_name": "Bogdan Olewnik",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Bogdan Olewnik"
    },
    "fe2897b6-2cdc-4f7c-aa71-05459c53cabb": {
        "unique_identifier": "fe2897b6-2cdc-4f7c-aa71-05459c53cabb",
        "person_name": "Bogdan Szwech",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Bogdan Szwech",
        "folder_name": "Bogdan Szwech",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Bogdan Szwech"
    },
    "e108ae4b-afb6-4160-985f-a4acfb15583b": {
        "unique_identifier": "e108ae4b-afb6-4160-985f-a4acfb15583b",
        "person_name": "Bogusława Chrzanowska zd. Kubicka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Bogusława Chrzanowska zd. Kubicka",
        "folder_name": "Bogusława Chrzanowska zd. Kubicka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Bogusława Chrzanowska zd. Kubicka"
    },
    "270019e0-3afb-4a01-8100-c4b573825c19": {
        "unique_identifier": "270019e0-3afb-4a01-8100-c4b573825c19",
        "person_name": "Bolesław Rutowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Bolesław Rutowski",
        "folder_name": "Bolesław Rutowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Bolesław Rutowski"
    },
    "6be4ee79-f089-4380-93cc-3152c7017611": {
        "unique_identifier": "6be4ee79-f089-4380-93cc-3152c7017611",
        "person_name": "Bolesław Zajkowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Bolesław Zajkowski",
        "folder_name": "Bolesław Zajkowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Bolesław Zajkowski"
    },
    "12623853-ec41-4401-8957-af3e47440af9": {
        "unique_identifier": "12623853-ec41-4401-8957-af3e47440af9",
        "person_name": "Bolesława Szwech zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Bolesława Szwech zd. Rutowska",
        "folder_name": "Bolesława Szwech zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Bolesława Szwech zd. Rutowska"
    },
    "b44147b2-6fc7-40ab-ad20-829799263474": {
        "unique_identifier": "b44147b2-6fc7-40ab-ad20-829799263474",
        "person_name": "Błażej Czajkowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Błażej Czajkowski",
        "folder_name": "Błażej Czajkowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Błażej Czajkowski"
    },
    "61d1411c-d147-47b2-8cd1-d2bab679553f": {
        "unique_identifier": "61d1411c-d147-47b2-8cd1-d2bab679553f",
        "person_name": "Czesława Kubicka zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Czesława Kubicka zd. Rutowska",
        "folder_name": "Czesława Kubicka zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Czesława Kubicka zd. Rutowska"
    },
    "32c81ef7-72c5-4c1c-93b9-56f62513feae": {
        "unique_identifier": "32c81ef7-72c5-4c1c-93b9-56f62513feae",
        "person_name": "Danuta Kowalska zd. Łodzkiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Danuta Kowalska zd. Łodzkiewicz",
        "folder_name": "Danuta Kowalska zd. Łodzkiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Danuta Kowalska zd. Łodzkiewicz"
    },
    "43bc1feb-c29c-459d-8b29-e6dd0887f396": {
        "unique_identifier": "43bc1feb-c29c-459d-8b29-e6dd0887f396",
        "person_name": "Danuta Zaremba zd. Misiak",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Danuta Zaremba zd. Misiak",
        "folder_name": "Danuta Zaremba zd. Misiak",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Danuta Zaremba zd. Misiak"
    },
    "115e5f09-bba6-4a6c-b1ce-b6232dbd2cb3": {
        "unique_identifier": "115e5f09-bba6-4a6c-b1ce-b6232dbd2cb3",
        "person_name": "Darek Surus",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Darek Surus",
        "folder_name": "Darek Surus",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Darek Surus"
    },
    "689a50c6-496a-493d-bcaa-ca6e0be1c0cb": {
        "unique_identifier": "689a50c6-496a-493d-bcaa-ca6e0be1c0cb",
        "person_name": "Dawid Łodzkiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Dawid Łodzkiewicz",
        "folder_name": "Dawid Łodzkiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Dawid Łodzkiewicz"
    },
    "81042da0-3fe5-4c41-a759-40baa97cb83d": {
        "unique_identifier": "81042da0-3fe5-4c41-a759-40baa97cb83d",
        "person_name": "Elżbieta Surus zd. Sobierajska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Elżbieta Surus zd. Sobierajska",
        "folder_name": "Elżbieta Surus zd. Sobierajska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Elżbieta Surus zd. Sobierajska"
    },
    "27676cc7-506f-4153-8e48-04cf45e14e0b": {
        "unique_identifier": "27676cc7-506f-4153-8e48-04cf45e14e0b",
        "person_name": "Ewa (nieznane) zd. Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Ewa (nieznane) zd. Krankiewicz",
        "folder_name": "Ewa (nieznane) zd. Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Ewa (nieznane) zd. Krankiewicz"
    },
    "3d2398c9-a96d-44c0-8782-9bf2d6fa0e96": {
        "unique_identifier": "3d2398c9-a96d-44c0-8782-9bf2d6fa0e96",
        "person_name": "Ewa Sobierajska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Ewa Sobierajska",
        "folder_name": "Ewa Sobierajska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Ewa Sobierajska"
    },
    "d39c2278-982b-4214-bf49-685d4de80382": {
        "unique_identifier": "d39c2278-982b-4214-bf49-685d4de80382",
        "person_name": "Feliks Sobierajski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Feliks Sobierajski",
        "folder_name": "Feliks Sobierajski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Feliks Sobierajski"
    },
    "e82a1530-9c9b-4e7d-ad4d-1f5b19149c7f": {
        "unique_identifier": "e82a1530-9c9b-4e7d-ad4d-1f5b19149c7f",
        "person_name": "Feliksa Rutowska zd. Łazińska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Feliksa Rutowska zd. Łazińska",
        "folder_name": "Feliksa Rutowska zd. Łazińska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Feliksa Rutowska zd. Łazińska"
    },
    "e7a5de25-7f45-4063-b441-a10823e6dded": {
        "unique_identifier": "e7a5de25-7f45-4063-b441-a10823e6dded",
        "person_name": "Florian Łędkowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Florian Łędkowski",
        "folder_name": "Florian Łędkowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Florian Łędkowski"
    },
    "55560fe0-deed-4f56-a64d-83ba2770893b": {
        "unique_identifier": "55560fe0-deed-4f56-a64d-83ba2770893b",
        "person_name": "Franciszek Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Franciszek Krankiewicz",
        "folder_name": "Franciszek Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Franciszek Krankiewicz"
    },
    "853c2128-b480-4f69-8ccd-abd601a133a2": {
        "unique_identifier": "853c2128-b480-4f69-8ccd-abd601a133a2",
        "person_name": "Franciszek Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Franciszek Matynka",
        "folder_name": "Franciszek Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Franciszek Matynka"
    },
    "c32fd741-9522-40ca-a0e3-2e32ac3b94d5": {
        "unique_identifier": "c32fd741-9522-40ca-a0e3-2e32ac3b94d5",
        "person_name": "Franciszek Rutowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Franciszek Rutowski",
        "folder_name": "Franciszek Rutowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Franciszek Rutowski"
    },
    "6670730e-55e5-43e8-bf2a-fdc26c5e1266": {
        "unique_identifier": "6670730e-55e5-43e8-bf2a-fdc26c5e1266",
        "person_name": "Franciszek Śliwiński",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Franciszek Śliwiński",
        "folder_name": "Franciszek Śliwiński",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Franciszek Śliwiński"
    },
    "e18583b7-ba9c-4986-8129-774386e67fce": {
        "unique_identifier": "e18583b7-ba9c-4986-8129-774386e67fce",
        "person_name": "Franciszka Śliwińska zd. Skowrońska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Franciszka Śliwińska zd. Skowrońska",
        "folder_name": "Franciszka Śliwińska zd. Skowrońska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Franciszka Śliwińska zd. Skowrońska"
    },
    "0a39bb7a-4293-4f1f-9e11-350aba26b92a": {
        "unique_identifier": "0a39bb7a-4293-4f1f-9e11-350aba26b92a",
        "person_name": "Halina Sobierajska zd. Sacharowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Halina Sobierajska zd. Sacharowska",
        "folder_name": "Halina Sobierajska zd. Sacharowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Halina Sobierajska zd. Sacharowska"
    },
    "a18fa0de-4066-4334-bf03-3793dcdf5cd0": {
        "unique_identifier": "a18fa0de-4066-4334-bf03-3793dcdf5cd0",
        "person_name": "Halina Świeczyńska zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Halina Świerczyńska zd. (niewiadomo)",
        "folder_name": "Halina Świerczyńska zd. (niewiadomo)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Halina Świerczyńska zd. (niewiadomo)"
    },
    "f313cf71-24bb-45e2-8bc2-652dd1eb4836": {
        "unique_identifier": "f313cf71-24bb-45e2-8bc2-652dd1eb4836",
        "person_name": "Helena Misiak zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Helena Misiak zd. Rutowska",
        "folder_name": "Helena Misiak zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Helena Misiak zd. Rutowska"
    },
    "ab75c9d0-b055-47a0-8d54-8e6fafbd1826": {
        "unique_identifier": "ab75c9d0-b055-47a0-8d54-8e6fafbd1826",
        "person_name": "Iwan Śpiewakowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Iwan Śpiewakowski",
        "folder_name": "Iwan Śpiewakowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Iwan Śpiewakowski"
    },
    "1dedf6e7-fc24-40b9-9f11-730657134062": {
        "unique_identifier": "1dedf6e7-fc24-40b9-9f11-730657134062",
        "person_name": "Jadwiga Czapska zd. Kubicka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jadwiga Czapska zd. Kubicka",
        "folder_name": "Jadwiga Czapska zd. Kubicka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jadwiga Czapska zd. Kubicka"
    },
    "9986406c-b7a8-4b85-b3be-26d26c290a14": {
        "unique_identifier": "9986406c-b7a8-4b85-b3be-26d26c290a14",
        "person_name": "Jadwiga Hajduk zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jadwiga Hajduk zd. (nieznane)",
        "folder_name": "Jadwiga Hajduk zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jadwiga Hajduk zd. (nieznane)"
    },
    "48111203-ddab-4dbc-8653-23b0fcf8f7a8": {
        "unique_identifier": "48111203-ddab-4dbc-8653-23b0fcf8f7a8",
        "person_name": "Jakub Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jakub Krankiewicz",
        "folder_name": "Jakub Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jakub Krankiewicz"
    },
    "57575a87-390a-4639-9ed5-94e7aae9408a": {
        "unique_identifier": "57575a87-390a-4639-9ed5-94e7aae9408a",
        "person_name": "Jan Chrzanowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jan Chrzanowski",
        "folder_name": "Jan Chrzanowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jan Chrzanowski"
    },
    "caf8ef7a-5ddc-4791-ad22-95371fdc3b5c": {
        "unique_identifier": "caf8ef7a-5ddc-4791-ad22-95371fdc3b5c",
        "person_name": "Jan Gwalbert Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jan Gwalbert Krankiewicz",
        "folder_name": "Jan Gwalbert Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jan Gwalbert Krankiewicz"
    },
    "350d9974-53cb-4a25-bbf9-89bb07c7217e": {
        "unique_identifier": "350d9974-53cb-4a25-bbf9-89bb07c7217e",
        "person_name": "Jan Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jan Krankiewicz",
        "folder_name": "Jan Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jan Krankiewicz"
    },
    "dee498b3-f969-44f0-b295-d18a039c7b99": {
        "unique_identifier": "dee498b3-f969-44f0-b295-d18a039c7b99",
        "person_name": "Jan Matynka (1)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jan Matynka (1)",
        "folder_name": "Jan Matynka (1)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jan Matynka (1)"
    },
    "7c1d3938-30a0-4ecb-9b53-fcbc33e985fd": {
        "unique_identifier": "7c1d3938-30a0-4ecb-9b53-fcbc33e985fd",
        "person_name": "Jan Matynka (2)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jan Matynka (2)",
        "folder_name": "Jan Matynka (2)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jan Matynka (2)"
    },
    "4f905dad-b28e-4bbf-ab6b-cf90a0d48c9d": {
        "unique_identifier": "4f905dad-b28e-4bbf-ab6b-cf90a0d48c9d",
        "person_name": "Jan Sobierajski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jan Sobierajski",
        "folder_name": "Jan Sobierajski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jan Sobierajski"
    },
    "81cd634d-17f6-45e7-893c-f205e8bf0e13": {
        "unique_identifier": "81cd634d-17f6-45e7-893c-f205e8bf0e13",
        "person_name": "Jan Łodzkiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jan Łodzkiewicz",
        "folder_name": "Jan Łodzkiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jan Łodzkiewicz"
    },
    "d6b52a33-f563-42f7-8fbf-8e35b9568b98": {
        "unique_identifier": "d6b52a33-f563-42f7-8fbf-8e35b9568b98",
        "person_name": "Jan Śliwiński (1)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jan Śliwiński (1)",
        "folder_name": "Jan Śliwiński (1)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jan Śliwiński (1)"
    },
    "bc482111-64b5-44a6-9975-8e9976b19e04": {
        "unique_identifier": "bc482111-64b5-44a6-9975-8e9976b19e04",
        "person_name": "Jan Śliwiński (2)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jan Śliwiński (2)",
        "folder_name": "Jan Śliwiński (2)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jan Śliwiński (2)"
    },
    "b2c8b41d-6501-4d84-b6d8-a63d623c8f87": {
        "unique_identifier": "b2c8b41d-6501-4d84-b6d8-a63d623c8f87",
        "person_name": "Janina Baranowska zd. Szwech",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Janina Baranowska zd. Szwech",
        "folder_name": "Janina Baranowska zd. Szwech",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Janina Baranowska zd. Szwech"
    },
    "6af37134-b853-4cc4-a25f-508f981e4ada": {
        "unique_identifier": "6af37134-b853-4cc4-a25f-508f981e4ada",
        "person_name": "Janina Sobierajska zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Janina Sobierajska zd. Rutowska",
        "folder_name": "Janina Sobierajska zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Janina Sobierajska zd. Rutowska"
    },
    "0ae90cc4-f30c-492b-98e3-629df8b9096f": {
        "unique_identifier": "0ae90cc4-f30c-492b-98e3-629df8b9096f",
        "person_name": "Jerzy Chrzanowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jerzy Chrzanowski",
        "folder_name": "Jerzy Chrzanowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jerzy Chrzanowski"
    },
    "f2c12854-da04-4215-aacc-ead894cbb079": {
        "unique_identifier": "f2c12854-da04-4215-aacc-ead894cbb079",
        "person_name": "Jerzy Kubicki",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jerzy Kubicki",
        "folder_name": "Jerzy Kubicki",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jerzy Kubicki"
    },
    "0af60691-7b33-4c6a-a796-2a2f2553d6f2": {
        "unique_identifier": "0af60691-7b33-4c6a-a796-2a2f2553d6f2",
        "person_name": "Jerzy Mankin",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jerzy Mankin",
        "folder_name": "Jerzy Mankin",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jerzy Mankin"
    },
    "0c281ac2-96ca-44c1-9ceb-583341b1b312": {
        "unique_identifier": "0c281ac2-96ca-44c1-9ceb-583341b1b312",
        "person_name": "Jerzy Łodzkiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Jerzy Łodzkiewicz",
        "folder_name": "Jerzy Łodzkiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Jerzy Łodzkiewicz"
    },
    "3ab3356c-1584-407d-ac0a-c3e10a8f431f": {
        "unique_identifier": "3ab3356c-1584-407d-ac0a-c3e10a8f431f",
        "person_name": "Julianna (nieznane) zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Julianna (nieznane) zd. Rutowska",
        "folder_name": "Julianna (nieznane) zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Julianna (nieznane) zd. Rutowska"
    },
    "812d408d-6b1d-402d-8c53-3fd8d844a351": {
        "unique_identifier": "812d408d-6b1d-402d-8c53-3fd8d844a351",
        "person_name": "Julianna Czajkowska zd. Łędkowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Julianna Czajkowska zd. Łędkowska",
        "folder_name": "Julianna Czajkowska zd. Łędkowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Julianna Czajkowska zd. Łędkowska"
    },
    "43337f53-27e9-4f67-9f78-37f4303800e3": {
        "unique_identifier": "43337f53-27e9-4f67-9f78-37f4303800e3",
        "person_name": "Józef Kalwasiński",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Józef Kalwasiński",
        "folder_name": "Józef Kalwasiński",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Józef Kalwasiński"
    },
    "b1c18c94-5c13-45c7-bcd0-93b61afacffb": {
        "unique_identifier": "b1c18c94-5c13-45c7-bcd0-93b61afacffb",
        "person_name": "Józef Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Józef Krankiewicz",
        "folder_name": "Józef Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Józef Krankiewicz"
    },
    "d7aa2f4b-ec7b-42af-8504-7592c6d3bde8": {
        "unique_identifier": "d7aa2f4b-ec7b-42af-8504-7592c6d3bde8",
        "person_name": "Józef Misiak",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Józef Misiak",
        "folder_name": "Józef Misiak",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Józef Misiak"
    },
    "58463f29-4f78-4b83-9e5c-b74bfa20597b": {
        "unique_identifier": "58463f29-4f78-4b83-9e5c-b74bfa20597b",
        "person_name": "Józef Rutowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Józef Rutowski",
        "folder_name": "Józef Rutowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Józef Rutowski"
    },
    "ca68a8af-59e1-4999-9ccb-4465ee8810f1": {
        "unique_identifier": "ca68a8af-59e1-4999-9ccb-4465ee8810f1",
        "person_name": "Józef Śliwiński",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Józef Śliwiński",
        "folder_name": "Józef Śliwiński",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Józef Śliwiński"
    },
    "e30c8cc2-0221-4084-8b11-09fae5f3878b": {
        "unique_identifier": "e30c8cc2-0221-4084-8b11-09fae5f3878b",
        "person_name": "Józefa (nieznane) zd. Czajkowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Józefa (nieznane) zd. Czajkowska",
        "folder_name": "Józefa (nieznane) zd. Czajkowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Józefa (nieznane) zd. Czajkowska"
    },
    "9989c92a-0f82-474a-a8f2-776055e787d6": {
        "unique_identifier": "9989c92a-0f82-474a-a8f2-776055e787d6",
        "person_name": "Józefa Kalwasińka zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Józefa Kalwasińka zd. Rutowska",
        "folder_name": "Józefa Kalwasińka zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Józefa Kalwasińka zd. Rutowska"
    },
    "670ab87f-6a76-44d1-b2cf-f81899a0940f": {
        "unique_identifier": "670ab87f-6a76-44d1-b2cf-f81899a0940f",
        "person_name": "Józefa Modziejewska zd. Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Józefa Modziejewska zd. Krankiewicz",
        "folder_name": "Józefa Modziejewska zd. Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Józefa Modziejewska zd. Krankiewicz"
    },
    "65f6d6bd-809b-4352-b311-e85a25d1485a": {
        "unique_identifier": "65f6d6bd-809b-4352-b311-e85a25d1485a",
        "person_name": "Józefa Rutowska zd. Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Józefa Rutowska zd. Matynka",
        "folder_name": "Józefa Rutowska zd. Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Józefa Rutowska zd. Matynka"
    },
    "68a45f0e-9070-4f77-aff7-cf5b72edd496": {
        "unique_identifier": "68a45f0e-9070-4f77-aff7-cf5b72edd496",
        "person_name": "Kamil Sobierajski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Kamil Sobierajski",
        "folder_name": "Kamil Sobierajski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Kamil Sobierajski"
    },
    "6e4d7ca6-1dc2-4931-9c92-e23392fea5d2": {
        "unique_identifier": "6e4d7ca6-1dc2-4931-9c92-e23392fea5d2",
        "person_name": "Katarzyna (nieznane) zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna (nieznane) zd. Rutowska",
        "folder_name": "Katarzyna (nieznane) zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna (nieznane) zd. Rutowska"
    },
    "311c343d-1b02-4d19-9309-c7b210d82454": {
        "unique_identifier": "311c343d-1b02-4d19-9309-c7b210d82454",
        "person_name": "Katarzyna (nieznane) zd. Śliwińska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna (nieznane) zd. Śliwińska",
        "folder_name": "Katarzyna (nieznane) zd. Śliwińska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna (nieznane) zd. Śliwińska"
    },
    "73092b3b-8842-4478-8609-a68166d71c72": {
        "unique_identifier": "73092b3b-8842-4478-8609-a68166d71c72",
        "person_name": "Katarzyna Julianna (nieznane) zd. Czajkowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna Julianna (nieznane) zd. Czajkowska",
        "folder_name": "Katarzyna Julianna (nieznane) zd. Czajkowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna Julianna (nieznane) zd. Czajkowska"
    },
    "7db9720a-1e45-4c7f-8ae9-d8d327d581b5": {
        "unique_identifier": "7db9720a-1e45-4c7f-8ae9-d8d327d581b5",
        "person_name": "Katarzyna Matynka zd. Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna Matynka zd. Krankiewicz",
        "folder_name": "Katarzyna Matynka zd. Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna Matynka zd. Krankiewicz"
    },
    "7e5dfad1-f9b5-4d2e-84bd-5c84d468cabf": {
        "unique_identifier": "7e5dfad1-f9b5-4d2e-84bd-5c84d468cabf",
        "person_name": "Katarzyna Rutowska zd. Sadowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna Rutowska zd. Sadowska",
        "folder_name": "Katarzyna Rutowska zd. Sadowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna Rutowska zd. Sadowska"
    },
    "2400fbcf-be6a-45e1-8b61-0088c2d8ca61": {
        "unique_identifier": "2400fbcf-be6a-45e1-8b61-0088c2d8ca61",
        "person_name": "Katarzyna Sadowska zd. Sułkowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna Sadowska zd. Sułkowska",
        "folder_name": "Katarzyna Sadowska zd. Sułkowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Katarzyna Sadowska zd. Sułkowska"
    },
    "0633853a-042b-48d6-be40-57cea66a8743": {
        "unique_identifier": "0633853a-042b-48d6-be40-57cea66a8743",
        "person_name": "Kazimiera Rutowska zd. Misiak",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Kazimiera Rutowska zd. Misiak",
        "folder_name": "Kazimiera Rutowska zd. Misiak",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Kazimiera Rutowska zd. Misiak"
    },
    "e2fd106a-5965-4e91-8552-a7dd612cd935": {
        "unique_identifier": "e2fd106a-5965-4e91-8552-a7dd612cd935",
        "person_name": "Kazimierz Czajkowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Kazimierz Czajkowski",
        "folder_name": "Kazimierz Czajkowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Kazimierz Czajkowski"
    },
    "40d325aa-7b99-48b6-b68a-bb394d453092": {
        "unique_identifier": "40d325aa-7b99-48b6-b68a-bb394d453092",
        "person_name": "Konstanty Śliwiński",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Konstanty Śliwiński",
        "folder_name": "Konstanty Śliwiński",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Konstanty Śliwiński"
    },
    "8585542c-20ef-4ef5-8af4-8354621043e1": {
        "unique_identifier": "8585542c-20ef-4ef5-8af4-8354621043e1",
        "person_name": "Krystyna Woźniakowska zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Krystyna Woźniakowska zd. Rutowska",
        "folder_name": "Krystyna Woźniakowska zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Krystyna Woźniakowska zd. Rutowska"
    },
    "b92b3479-e5e2-48b5-bfa4-1f55f0adf7b1": {
        "unique_identifier": "b92b3479-e5e2-48b5-bfa4-1f55f0adf7b1",
        "person_name": "Leokadia (nieznane) zd. Misiak",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Leokadia (nieznane) zd. Misiak",
        "folder_name": "Leokadia (nieznane) zd. Misiak",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Leokadia (nieznane) zd. Misiak"
    },
    "2be7e1ea-edf1-4fa6-850a-f44512a7d937": {
        "unique_identifier": "2be7e1ea-edf1-4fa6-850a-f44512a7d937",
        "person_name": "Leokadia Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Leokadia Matynka",
        "folder_name": "Leokadia Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Leokadia Matynka"
    },
    "515e4ade-337c-4dcc-a8ca-7c10027fc3b3": {
        "unique_identifier": "515e4ade-337c-4dcc-a8ca-7c10027fc3b3",
        "person_name": "Leokadia Łodzkiewicz zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Leokadia Łodzkiewicz zd. Rutowska",
        "folder_name": "Leokadia Łodzkiewicz zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Leokadia Łodzkiewicz zd. Rutowska"
    },
    "6e2ef2de-fae7-4a31-8cb5-9601d8b6856f": {
        "unique_identifier": "6e2ef2de-fae7-4a31-8cb5-9601d8b6856f",
        "person_name": "Leon Rutowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Leon Rutowski",
        "folder_name": "Leon Rutowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Leon Rutowski"
    },
    "ad56b08d-6302-4b2c-b5c9-a084948ccb0f": {
        "unique_identifier": "ad56b08d-6302-4b2c-b5c9-a084948ccb0f",
        "person_name": "Leszek Sobierajski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Leszek Sobierajski",
        "folder_name": "Leszek Sobierajski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Leszek Sobierajski"
    },
    "cac01965-10ca-42e7-896e-deeb521681ec": {
        "unique_identifier": "cac01965-10ca-42e7-896e-deeb521681ec",
        "person_name": "Lidia Sobierajska zd. Hajduk",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Lidia Sobierajska zd. Hajduk",
        "folder_name": "Lidia Sobierajska zd. Hajduk",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Lidia Sobierajska zd. Hajduk"
    },
    "be53c431-2902-49bb-873a-3adc63ed1022": {
        "unique_identifier": "be53c431-2902-49bb-873a-3adc63ed1022",
        "person_name": "Magdalena (nieznane) zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Magdalena (nieznane) zd. Rutowska",
        "folder_name": "Magdalena (nieznane) zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Magdalena (nieznane) zd. Rutowska"
    },
    "53baf90b-14e2-412d-94ee-9242cee28bf5": {
        "unique_identifier": "53baf90b-14e2-412d-94ee-9242cee28bf5",
        "person_name": "Marcin Dydak",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marcin Dydak",
        "folder_name": "Marcin Dydak",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marcin Dydak"
    },
    "6baa5912-ee9d-422d-ad2a-0907b64b38cb": {
        "unique_identifier": "6baa5912-ee9d-422d-ad2a-0907b64b38cb",
        "person_name": "Marcin Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marcin Matynka",
        "folder_name": "Marcin Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marcin Matynka"
    },
    "13a725cc-2998-4bc1-8e18-0b2c7039e41a": {
        "unique_identifier": "13a725cc-2998-4bc1-8e18-0b2c7039e41a",
        "person_name": "Marcjanna Kowalska zd. Śpiewakowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marcjanna Kowalska zd. Śpiewakowska",
        "folder_name": "Marcjanna Kowalska zd. Śpiewakowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marcjanna Kowalska zd. Śpiewakowska"
    },
    "6dd3b849-4da5-4202-87b9-a92a072dce88": {
        "unique_identifier": "6dd3b849-4da5-4202-87b9-a92a072dce88",
        "person_name": "Marcjanna Matynka zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marcjanna Matynka zd. (nieznane)",
        "folder_name": "Marcjanna Matynka zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marcjanna Matynka zd. (nieznane)"
    },
    "7643e953-3228-4069-aaeb-f22e305e60eb": {
        "unique_identifier": "7643e953-3228-4069-aaeb-f22e305e60eb",
        "person_name": "Maria (nieznane) zd. Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Maria (nieznane) zd. Matynka",
        "folder_name": "Maria (nieznane) zd. Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Maria (nieznane) zd. Matynka"
    },
    "e0abe1a5-f247-4b6e-8f18-590331cc3ee7": {
        "unique_identifier": "e0abe1a5-f247-4b6e-8f18-590331cc3ee7",
        "person_name": "Marian Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marian Krankiewicz",
        "folder_name": "Marian Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marian Krankiewicz"
    },
    "a8eeea45-9f5a-451c-b814-be8c1c6096ba": {
        "unique_identifier": "a8eeea45-9f5a-451c-b814-be8c1c6096ba",
        "person_name": "Marian Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marian Matynka",
        "folder_name": "Marian Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marian Matynka"
    },
    "fab91dc7-1502-4e42-8546-5ffa250376eb": {
        "unique_identifier": "fab91dc7-1502-4e42-8546-5ffa250376eb",
        "person_name": "Marianna (nieznane) zd. Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marianna (nieznane) zd. Krankiewicz (1)",
        "folder_name": "Marianna (nieznane) zd. Krankiewicz (1)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marianna (nieznane) zd. Krankiewicz (1)"
    },
    "82fc8d32-387f-469d-87f1-3f0206f17c07": {
        "unique_identifier": "82fc8d32-387f-469d-87f1-3f0206f17c07",
        "person_name": "Marianna (nieznane) zd. Krankiewicz (2)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marianna (nieznane) zd. Krankiewicz (2)",
        "folder_name": "Marianna (nieznane) zd. Krankiewicz (2)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marianna (nieznane) zd. Krankiewicz (2)"
    },
    "bd6f57da-44f3-40a4-b47c-7e5d89bc143b": {
        "unique_identifier": "bd6f57da-44f3-40a4-b47c-7e5d89bc143b",
        "person_name": "Marianna Czajkowska zd. Gałczyńska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marianna Czajkowska zd. Gałczyńska",
        "folder_name": "Marianna Czajkowska zd. Gałczyńska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marianna Czajkowska zd. Gałczyńska"
    },
    "93fe98b0-15fa-41cc-a709-ae28595de0d3": {
        "unique_identifier": "93fe98b0-15fa-41cc-a709-ae28595de0d3",
        "person_name": "Marianna Krankiewicz zd. Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marianna Krankiewicz zd. Matynka",
        "folder_name": "Marianna Krankiewicz zd. Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marianna Krankiewicz zd. Matynka"
    },
    "087463ea-17ca-4bb9-94e9-ac88c62e86aa": {
        "unique_identifier": "087463ea-17ca-4bb9-94e9-ac88c62e86aa",
        "person_name": "Marianna Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marianna Matynka",
        "folder_name": "Marianna Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marianna Matynka"
    },
    "202f293d-68a1-4fa4-b761-bdda75ef2939": {
        "unique_identifier": "202f293d-68a1-4fa4-b761-bdda75ef2939",
        "person_name": "Marianna Olewnik zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marianna Olewnik zd. Rutowska",
        "folder_name": "Marianna Olewnik zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marianna Olewnik zd. Rutowska"
    },
    "e6242355-5a21-4af9-9747-e325b2c4999e": {
        "unique_identifier": "e6242355-5a21-4af9-9747-e325b2c4999e",
        "person_name": "Marianna Rutowska zd. Alabrudzińska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marianna Rutowska zd. Alabrudzińska",
        "folder_name": "Marianna Rutowska zd. Alabrudzińska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marianna Rutowska zd. Alabrudzińska"
    },
    "9390a245-c33a-436a-969b-8b7d91ca2a62": {
        "unique_identifier": "9390a245-c33a-436a-969b-8b7d91ca2a62",
        "person_name": "Marianna Sobierajska zd. Człapińska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Marianna Sobierajska zd. Człapińska",
        "folder_name": "Marianna Sobierajska zd. Człapińska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Marianna Sobierajska zd. Człapińska"
    },
    "0e604c6b-2d18-4b2b-99f4-7d9798a62fbb": {
        "unique_identifier": "0e604c6b-2d18-4b2b-99f4-7d9798a62fbb",
        "person_name": "Mateusz Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Mateusz Krankiewicz",
        "folder_name": "Mateusz Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Mateusz Krankiewicz"
    },
    "ec03c9b2-fc15-4af0-93dd-aaac9b4be615": {
        "unique_identifier": "ec03c9b2-fc15-4af0-93dd-aaac9b4be615",
        "person_name": "Małgorzata Łędkowska zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Małgorzata Łędkowska zd. (nieznane)",
        "folder_name": "Małgorzata Łędkowska zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Małgorzata Łędkowska zd. (nieznane)"
    },
    "99719aa7-be89-40ba-b40f-78da63e07880": {
        "unique_identifier": "99719aa7-be89-40ba-b40f-78da63e07880",
        "person_name": "Michał Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Michał Matynka",
        "folder_name": "Michał Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Michał Matynka"
    },
    "e766056d-dd9f-4c17-846e-15cef5bdf9ac": {
        "unique_identifier": "e766056d-dd9f-4c17-846e-15cef5bdf9ac",
        "person_name": "Mieczysław Hajduk",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Mieczysław Hajduk",
        "folder_name": "Mieczysław Hajduk",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Mieczysław Hajduk"
    },
    "d85a9262-0afd-4ed5-9bcc-03d49be7c22a": {
        "unique_identifier": "d85a9262-0afd-4ed5-9bcc-03d49be7c22a",
        "person_name": "Mieczysław Olewnik",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Mieczysław Olewnik",
        "folder_name": "Mieczysław Olewnik",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Mieczysław Olewnik"
    },
    "598086b5-23cd-4155-b6cb-18c08401cff3": {
        "unique_identifier": "598086b5-23cd-4155-b6cb-18c08401cff3",
        "person_name": "Mirosław Łodzkiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Mirosław Łodzkiewicz",
        "folder_name": "Mirosław Łodzkiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Mirosław Łodzkiewicz"
    },
    "cff3821e-51a9-4752-83df-5912ef003321": {
        "unique_identifier": "cff3821e-51a9-4752-83df-5912ef003321",
        "person_name": "Monika Kowalska zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Monika Kowalska zd. (nieznane)",
        "folder_name": "Monika Kowalska zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Monika Kowalska zd. (nieznane)"
    },
    "86788d72-eae4-44b2-9703-11c405d34e24": {
        "unique_identifier": "86788d72-eae4-44b2-9703-11c405d34e24",
        "person_name": "Paulina Kowalska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Paulina Kowalska",
        "folder_name": "Paulina Kowalska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Paulina Kowalska"
    },
    "b43038fb-3053-4a0c-beac-3311e24f30c4": {
        "unique_identifier": "b43038fb-3053-4a0c-beac-3311e24f30c4",
        "person_name": "Paweł Chrzanowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Paweł Chrzanowski",
        "folder_name": "Paweł Chrzanowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Paweł Chrzanowski"
    },
    "b5ffa427-5451-4b0a-b278-599d647f4ec2": {
        "unique_identifier": "b5ffa427-5451-4b0a-b278-599d647f4ec2",
        "person_name": "Paweł Rutowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Paweł Rutowski",
        "folder_name": "Paweł Rutowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Paweł Rutowski"
    },
    "6afd9a76-b62a-4e42-93aa-1252b755bbd3": {
        "unique_identifier": "6afd9a76-b62a-4e42-93aa-1252b755bbd3",
        "person_name": "Przemysław Łodzkiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Przemysław Łodzkiewicz",
        "folder_name": "Przemysław Łodzkiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Przemysław Łodzkiewicz"
    },
    "8225ee06-0cd6-4ea0-9f02-2eaa4b6d6888": {
        "unique_identifier": "8225ee06-0cd6-4ea0-9f02-2eaa4b6d6888",
        "person_name": "Regina Misiak zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Regina Misiak zd. Rutowska",
        "folder_name": "Regina Misiak zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Regina Misiak zd. Rutowska"
    },
    "276f45fa-3f87-4a94-8abd-4fb0e0223037": {
        "unique_identifier": "276f45fa-3f87-4a94-8abd-4fb0e0223037",
        "person_name": "Renata Łodzkiewicz zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Renata Łodzkiewicz zd. (nieznane)",
        "folder_name": "Renata Łodzkiewicz zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Renata Łodzkiewicz zd. (nieznane)"
    },
    "932277c8-191b-4e00-a873-2c82ae2b3f8f": {
        "unique_identifier": "932277c8-191b-4e00-a873-2c82ae2b3f8f",
        "person_name": "Roman Rutowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Roman Rutowski",
        "folder_name": "Roman Rutowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Roman Rutowski"
    },
    "34cfeb44-525e-460e-9a54-74bede0424ce": {
        "unique_identifier": "34cfeb44-525e-460e-9a54-74bede0424ce",
        "person_name": "Ryszard Surus",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Ryszard Surus",
        "folder_name": "Ryszard Surus",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Ryszard Surus"
    },
    "81c260e0-6a82-43b7-bcbf-67806a2917fe": {
        "unique_identifier": "81c260e0-6a82-43b7-bcbf-67806a2917fe",
        "person_name": "Sebastian Kowalski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Sebastian Kowalski",
        "folder_name": "Sebastian Kowalski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Sebastian Kowalski"
    },
    "9a3fdef3-8b5a-4dc4-9cb7-7c0fa84224c2": {
        "unique_identifier": "9a3fdef3-8b5a-4dc4-9cb7-7c0fa84224c2",
        "person_name": "Stanisław Czajkowski (1)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Czajkowski (1)",
        "folder_name": "Stanisław Czajkowski (1)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Czajkowski (1)"
    },
    "b41cefa4-73e1-470d-918f-9ab7b94ae303": {
        "unique_identifier": "b41cefa4-73e1-470d-918f-9ab7b94ae303",
        "person_name": "Stanisław Czajkowski (2)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Czajkowski (2)",
        "folder_name": "Stanisław Czajkowski (2)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Czajkowski (2)"
    },
    "4e50d764-11ad-4c0b-948d-ada3eb8b5af2": {
        "unique_identifier": "4e50d764-11ad-4c0b-948d-ada3eb8b5af2",
        "person_name": "Stanisław Czapski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Czapski",
        "folder_name": "Stanisław Czapski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Czapski"
    },
    "c1d757f2-0ef3-44c0-b8ba-31ee62e887c8": {
        "unique_identifier": "c1d757f2-0ef3-44c0-b8ba-31ee62e887c8",
        "person_name": "Stanisław Lewandowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Lewandowski",
        "folder_name": "Stanisław Lewandowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Lewandowski"
    },
    "c40f8e10-74ce-4924-a91b-648c84ecece2": {
        "unique_identifier": "c40f8e10-74ce-4924-a91b-648c84ecece2",
        "person_name": "Stanisław Olewnik",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Olewnik",
        "folder_name": "Stanisław Olewnik",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Stanisław Olewnik"
    },
    "6aed5a67-32f4-4e76-9e15-fa21a12ceef1": {
        "unique_identifier": "6aed5a67-32f4-4e76-9e15-fa21a12ceef1",
        "person_name": "Stanisława (nieznane) zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Stanisława (nieznane) zd. Rutowska",
        "folder_name": "Stanisława (nieznane) zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Stanisława (nieznane) zd. Rutowska"
    },
    "93be2751-f383-4c2b-9e12-b5763bc22aa4": {
        "unique_identifier": "93be2751-f383-4c2b-9e12-b5763bc22aa4",
        "person_name": "Stanisława Górecka zd. Szwech",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Stanisława Górecka zd. Szwech",
        "folder_name": "Stanisława Górecka zd. Szwech",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Stanisława Górecka zd. Szwech"
    },
    "e39dce72-3b4e-4bad-a2c6-174381332053": {
        "unique_identifier": "e39dce72-3b4e-4bad-a2c6-174381332053",
        "person_name": "Sylwia Sobierajska zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Sylwia Sobierajska zd. (nieznane)",
        "folder_name": "Sylwia Sobierajska zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Sylwia Sobierajska zd. (nieznane)"
    },
    "19b0513f-cf8d-4405-a8be-b5f7a6b4be49": {
        "unique_identifier": "19b0513f-cf8d-4405-a8be-b5f7a6b4be49",
        "person_name": "Szczepan Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Szczepan Matynka",
        "folder_name": "Szczepan Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Szczepan Matynka"
    },
    "ecc477af-a8b1-45cb-9651-ca9ba913794d": {
        "unique_identifier": "ecc477af-a8b1-45cb-9651-ca9ba913794d",
        "person_name": "Szymon Czajkowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Szymon Czajkowski",
        "folder_name": "Szymon Czajkowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Szymon Czajkowski"
    },
    "8f5bf489-bdab-461d-9866-0da1f67fe382": {
        "unique_identifier": "8f5bf489-bdab-461d-9866-0da1f67fe382",
        "person_name": "Tekla Dydak zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Tekla Dydak zd. (nieznane)",
        "folder_name": "Tekla Dydak zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Tekla Dydak zd. (nieznane)"
    },
    "769847ac-5165-43a7-8c2c-de1102a9083f": {
        "unique_identifier": "769847ac-5165-43a7-8c2c-de1102a9083f",
        "person_name": "Tekla Rutowska zd. Śliwińska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Tekla Rutowska zd. Śliwińska",
        "folder_name": "Tekla Rutowska zd. Śliwińska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Tekla Rutowska zd. Śliwińska"
    },
    "3c14caa9-6230-4977-945d-53db51d65f8f": {
        "unique_identifier": "3c14caa9-6230-4977-945d-53db51d65f8f",
        "person_name": "Teofila Matynka zd. Dydak;Dydo",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Teofila Matynka zd. Dydak;Dydo",
        "folder_name": "Teofila Matynka zd. Dydak;Dydo",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Teofila Matynka zd. Dydak;Dydo"
    },
    "857d5dde-736c-4004-b094-127d2982ab47": {
        "unique_identifier": "857d5dde-736c-4004-b094-127d2982ab47",
        "person_name": "Teresa Lewandowska zd. Kubicka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Teresa Lewandowska zd. Kubicka",
        "folder_name": "Teresa Lewandowska zd. Kubicka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Teresa Lewandowska zd. Kubicka"
    },
    "37dfa705-0cb5-419c-afed-d5d69b757634": {
        "unique_identifier": "37dfa705-0cb5-419c-afed-d5d69b757634",
        "person_name": "Tomasz Surus",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Tomasz Surus",
        "folder_name": "Tomasz Surus",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Tomasz Surus"
    },
    "b6ad7b45-5d7d-4644-9ef3-bda79646696b": {
        "unique_identifier": "b6ad7b45-5d7d-4644-9ef3-bda79646696b",
        "person_name": "Waleria Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Waleria Rutowska",
        "folder_name": "Waleria Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Waleria Rutowska"
    },
    "ecc0f359-57d9-4567-94f9-ba71f353d8ff": {
        "unique_identifier": "ecc0f359-57d9-4567-94f9-ba71f353d8ff",
        "person_name": "Wanda (nieznane) zd. Matynka",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Wanda (nieznane) zd. Matynka",
        "folder_name": "Wanda (nieznane) zd. Matynka",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Wanda (nieznane) zd. Matynka"
    },
    "27ce913b-4cbb-4292-a937-38d599b0df6d": {
        "unique_identifier": "27ce913b-4cbb-4292-a937-38d599b0df6d",
        "person_name": "Wanda (nieznane) zd. Szwech",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Wanda (nieznane) zd. Szwech",
        "folder_name": "Wanda (nieznane) zd. Szwech",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Wanda (nieznane) zd. Szwech"
    },
    "b3e2172f-0572-4681-b1c6-f4fa2ccbfac1": {
        "unique_identifier": "b3e2172f-0572-4681-b1c6-f4fa2ccbfac1",
        "person_name": "Wawrzyniec Śliwiński",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Wawrzyniec Śliwiński",
        "folder_name": "Wawrzyniec Śliwiński",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Wawrzyniec Śliwiński"
    },
    "e878254f-9ef3-4995-8904-98995de29127": {
        "unique_identifier": "e878254f-9ef3-4995-8904-98995de29127",
        "person_name": "Weronika Zimna zd. Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Weronika Zimna zd. Krankiewicz",
        "folder_name": "Weronika Zimna zd. Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Weronika Zimna zd. Krankiewicz"
    },
    "bdfa13d1-1796-4be8-a244-9bf2e2867662": {
        "unique_identifier": "bdfa13d1-1796-4be8-a244-9bf2e2867662",
        "person_name": "Wojciech Czajkowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Wojciech Czajkowski",
        "folder_name": "Wojciech Czajkowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Wojciech Czajkowski"
    },
    "7fae8cda-ecb6-4bff-94dc-607f3ef197d7": {
        "unique_identifier": "7fae8cda-ecb6-4bff-94dc-607f3ef197d7",
        "person_name": "Wojciech Krankiewicz",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Wojciech Krankiewicz",
        "folder_name": "Wojciech Krankiewicz",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Wojciech Krankiewicz"
    },
    "09336970-aa2c-42a7-9efd-adfc2a0fbebb": {
        "unique_identifier": "09336970-aa2c-42a7-9efd-adfc2a0fbebb",
        "person_name": "Władysław Szwech",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Władysław Szwech",
        "folder_name": "Władysław Szwech",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Władysław Szwech"
    },
    "3dea3dc1-1e55-4059-b21d-d49137ff4e9a": {
        "unique_identifier": "3dea3dc1-1e55-4059-b21d-d49137ff4e9a",
        "person_name": "Władysława Szwech",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Władysława Szwech",
        "folder_name": "Władysława Szwech",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Władysława Szwech"
    },
    "d51d5e26-60af-4629-9024-4aabff660195": {
        "unique_identifier": "d51d5e26-60af-4629-9024-4aabff660195",
        "person_name": "Zbigniew Chrzanowski",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Zbigniew Chrzanowski",
        "folder_name": "Zbigniew Chrzanowski",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Zbigniew Chrzanowski"
    },
    "167af500-5d92-4e51-baaf-5f396661726c": {
        "unique_identifier": "167af500-5d92-4e51-baaf-5f396661726c",
        "person_name": "Zofia Mankin zd. Rutowska",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Zofia Mankin zd. Rutowska",
        "folder_name": "Zofia Mankin zd. Rutowska",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Zofia Mankin zd. Rutowska"
    },
    "ca2e000f-3ee2-404c-93d3-c4d5f5661b09": {
        "unique_identifier": "ca2e000f-3ee2-404c-93d3-c4d5f5661b09",
        "person_name": "Zofia Matynka zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Zofia Matynka zd. (nieznane)",
        "folder_name": "Zofia Matynka zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Zofia Matynka zd. (nieznane)"
    },
    "f6b61f29-48aa-4529-8382-161628b164d1": {
        "unique_identifier": "f6b61f29-48aa-4529-8382-161628b164d1",
        "person_name": "Zofia Zajkowska zd. Olewnik",
        "location": "C:\\Sorted tree\\People\\Rutowski\\Zofia Zajkowska zd. Olewnik",
        "folder_name": "Zofia Zajkowska zd. Olewnik",
        "folder_path": "C:\\Sorted tree\\People\\Rutowski\\Zofia Zajkowska zd. Olewnik"
    },
    "32bcd5a2-7414-4fd7-9f48-8038803d0431": {
        "unique_identifier": "32bcd5a2-7414-4fd7-9f48-8038803d0431",
        "person_name": "(nieznane) Kossowska zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\(nieznane) Kossowska zd. (nieznane)",
        "folder_name": "(nieznane) Kossowska zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\(nieznane) Kossowska zd. (nieznane)"
    },
    "d75dae13-f303-4eec-92b6-ba22605776b7": {
        "unique_identifier": "d75dae13-f303-4eec-92b6-ba22605776b7",
        "person_name": "(nieznane) Kossowski",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\(nieznane) Kossowski",
        "folder_name": "(nieznane) Kossowski",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\(nieznane) Kossowski"
    },
    "136d98fb-2b22-4fc5-a4e9-7ac7f12b4ea8": {
        "unique_identifier": "136d98fb-2b22-4fc5-a4e9-7ac7f12b4ea8",
        "person_name": "Adam Oleksy",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Adam Oleksy",
        "folder_name": "Adam Oleksy",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Adam Oleksy"
    },
    "a7f128b9-8d2f-4fc6-9cd7-023897c1e707": {
        "unique_identifier": "a7f128b9-8d2f-4fc6-9cd7-023897c1e707",
        "person_name": "Agnieszka Jakubowska zd. Smerecka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Agnieszka Jakubowska zd. Smerecka",
        "folder_name": "Agnieszka Jakubowska zd. Smerecka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Agnieszka Jakubowska zd. Smerecka"
    },
    "302120b4-d3fa-4e74-b2b6-0955427d6257": {
        "unique_identifier": "302120b4-d3fa-4e74-b2b6-0955427d6257",
        "person_name": "Anna (nieznane) zd. Kuziel",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Anna (nieznane) zd. Kuziel",
        "folder_name": "Anna (nieznane) zd. Kuziel",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Anna (nieznane) zd. Kuziel"
    },
    "485f40a7-8145-4965-a727-61ac3be5b7a4": {
        "unique_identifier": "485f40a7-8145-4965-a727-61ac3be5b7a4",
        "person_name": "Anna Staluszka zd. Srzednicka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Anna Staluszka zd. Srzednicka",
        "folder_name": "Anna Staluszka zd. Srzednicka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Anna Staluszka zd. Srzednicka"
    },
    "1ad5590c-7444-4149-93b9-4c866beeb7d8": {
        "unique_identifier": "1ad5590c-7444-4149-93b9-4c866beeb7d8",
        "person_name": "Antoni Stanuch",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Antoni Stanuch",
        "folder_name": "Antoni Stanuch",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Antoni Stanuch"
    },
    "c8e52a33-25da-4074-a527-b77fad4deb4e": {
        "unique_identifier": "c8e52a33-25da-4074-a527-b77fad4deb4e",
        "person_name": "Barbara Stanuch zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Barbara Stanuch zd. (nieznane)",
        "folder_name": "Barbara Stanuch zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Barbara Stanuch zd. (nieznane)"
    },
    "88300f6d-eca9-4637-b5f3-5b98b275efe0": {
        "unique_identifier": "88300f6d-eca9-4637-b5f3-5b98b275efe0",
        "person_name": "Bożena Oleksy zd. Smerecka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Bożena Oleksy zd. Smerecka",
        "folder_name": "Bożena Oleksy zd. Smerecka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Bożena Oleksy zd. Smerecka"
    },
    "f33fc36d-48eb-4b76-889d-7c366893e77f": {
        "unique_identifier": "f33fc36d-48eb-4b76-889d-7c366893e77f",
        "person_name": "Dzidka Podremańska zd. Biela",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Dzidka Podremańska zd. Biela",
        "folder_name": "Dzidka Podremańska zd. Biela",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Dzidka Podremańska zd. Biela"
    },
    "8990eaed-62eb-4830-932d-47502bb0ca2a": {
        "unique_identifier": "8990eaed-62eb-4830-932d-47502bb0ca2a",
        "person_name": "Eryk Srzednicki",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Eryk Srzednicki",
        "folder_name": "Eryk Srzednicki",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Eryk Srzednicki"
    },
    "994fa1c9-78ff-4359-a61b-3eb18acf0585": {
        "unique_identifier": "994fa1c9-78ff-4359-a61b-3eb18acf0585",
        "person_name": "Ewa Fiutka zd. Srzednicka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Ewa Fiutka zd. Srzednicka",
        "folder_name": "Ewa Fiutka zd. Srzednicka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Ewa Fiutka zd. Srzednicka"
    },
    "0e858015-25bc-40ca-83fd-12836a02bbd1": {
        "unique_identifier": "0e858015-25bc-40ca-83fd-12836a02bbd1",
        "person_name": "Franciszka Srzednicka zd. Kuziel",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Franciszka Srzednicka zd. Kuziel",
        "folder_name": "Franciszka Srzednicka zd. Kuziel",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Franciszka Srzednicka zd. Kuziel"
    },
    "90db933a-e4f7-4f77-a375-e299f3486eac": {
        "unique_identifier": "90db933a-e4f7-4f77-a375-e299f3486eac",
        "person_name": "Genowefa Srzednicka zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Genowefa Srzednicka zd. (nieznane)",
        "folder_name": "Genowefa Srzednicka zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Genowefa Srzednicka zd. (nieznane)"
    },
    "68fff21f-e6ac-4ef5-b5f4-f01d599ac094": {
        "unique_identifier": "68fff21f-e6ac-4ef5-b5f4-f01d599ac094",
        "person_name": "Grażyna Smerecka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Grażyna Smerecka",
        "folder_name": "Grażyna Smerecka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Grażyna Smerecka"
    },
    "c0e19c25-df74-4d77-8ded-0dae4612510a": {
        "unique_identifier": "c0e19c25-df74-4d77-8ded-0dae4612510a",
        "person_name": "Helena (nieznane) zd. Kuziel",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Helena (nieznane) zd. Kuziel",
        "folder_name": "Helena (nieznane) zd. Kuziel",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Helena (nieznane) zd. Kuziel"
    },
    "fc0e3b85-fdd2-41a8-85a6-2439b59185cc": {
        "unique_identifier": "fc0e3b85-fdd2-41a8-85a6-2439b59185cc",
        "person_name": "Irena (nieznane) zd. Biela",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Irena (nieznane) zd. Biela",
        "folder_name": "Irena (nieznane) zd. Biela",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Irena (nieznane) zd. Biela"
    },
    "f992b57e-93c8-4cff-a2ce-0ae51cab539b": {
        "unique_identifier": "f992b57e-93c8-4cff-a2ce-0ae51cab539b",
        "person_name": "Jadwiga Smerecka zd. Srzednicka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Jadwiga Smerecka zd. Srzednicka",
        "folder_name": "Jadwiga Smerecka zd. Srzednicka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Jadwiga Smerecka zd. Srzednicka"
    },
    "0b1a751b-dadf-436d-9882-ac00a47e7fd7": {
        "unique_identifier": "0b1a751b-dadf-436d-9882-ac00a47e7fd7",
        "person_name": "Jadwiga Sternalska zd. Stanuch",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Jadwiga Sternalska zd. Stanuch",
        "folder_name": "Jadwiga Sternalska zd. Stanuch",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Jadwiga Sternalska zd. Stanuch"
    },
    "96f8bf75-f311-4e95-9f20-2470935b770e": {
        "unique_identifier": "96f8bf75-f311-4e95-9f20-2470935b770e",
        "person_name": "Jan Srzednicki (1)",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Jan Srzednicki (1)",
        "folder_name": "Jan Srzednicki (1)",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Jan Srzednicki (1)"
    },
    "b42b514f-0c51-4979-b9f7-120743536d16": {
        "unique_identifier": "b42b514f-0c51-4979-b9f7-120743536d16",
        "person_name": "Jan Srzednicki (2)",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Jan Srzednicki (2)",
        "folder_name": "Jan Srzednicki (2)",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Jan Srzednicki (2)"
    },
    "7383e069-35c5-4b9e-8101-266a29ea93aa": {
        "unique_identifier": "7383e069-35c5-4b9e-8101-266a29ea93aa",
        "person_name": "Jerzy Srzednicki",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Jerzy Srzednicki",
        "folder_name": "Jerzy Srzednicki",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Jerzy Srzednicki"
    },
    "0480bf11-39e3-41b7-9426-0307fd36f37d": {
        "unique_identifier": "0480bf11-39e3-41b7-9426-0307fd36f37d",
        "person_name": "Julian Srzednicki",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Julian Srzednicki",
        "folder_name": "Julian Srzednicki",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Julian Srzednicki"
    },
    "b53e5f66-634d-4e79-9822-bf2294da43a2": {
        "unique_identifier": "b53e5f66-634d-4e79-9822-bf2294da43a2",
        "person_name": "Kamila (nieznane) zd. Oleksy",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Kamila (nieznane) zd. Oleksy",
        "folder_name": "Kamila (nieznane) zd. Oleksy",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Kamila (nieznane) zd. Oleksy"
    },
    "e551f429-6485-49cb-abb9-697af33067eb": {
        "unique_identifier": "e551f429-6485-49cb-abb9-697af33067eb",
        "person_name": "Kamila (nieznane) zd. Stanuch",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Kamila (nieznane) zd. Stanuch",
        "folder_name": "Kamila (nieznane) zd. Stanuch",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Kamila (nieznane) zd. Stanuch"
    },
    "f30d5126-f211-4953-a77b-9168d377ad18": {
        "unique_identifier": "f30d5126-f211-4953-a77b-9168d377ad18",
        "person_name": "Kinga Kaseja zd. Smerecka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Kinga Kaseja zd. Smerecka",
        "folder_name": "Kinga Kaseja zd. Smerecka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Kinga Kaseja zd. Smerecka"
    },
    "ceb6f30a-97bf-4ade-8d65-a28ed2d8417c": {
        "unique_identifier": "ceb6f30a-97bf-4ade-8d65-a28ed2d8417c",
        "person_name": "Kunegunda Kuziel zd. Kossowska",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Kunegunda Kuziel zd. Kossowska",
        "folder_name": "Kunegunda Kuziel zd. Kossowska",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Kunegunda Kuziel zd. Kossowska"
    },
    "e6001ba4-f702-4366-af5e-4c357fa54f57": {
        "unique_identifier": "e6001ba4-f702-4366-af5e-4c357fa54f57",
        "person_name": "Leon Kuziel",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Leon Kuziel",
        "folder_name": "Leon Kuziel",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Leon Kuziel"
    },
    "68f22ab9-2e66-4933-9ec5-cb973fec58d4": {
        "unique_identifier": "68f22ab9-2e66-4933-9ec5-cb973fec58d4",
        "person_name": "Lucjan Srzednicki",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Lucjan Srzednicki",
        "folder_name": "Lucjan Srzednicki",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Lucjan Srzednicki"
    },
    "a69fd0f7-ce06-492a-a49c-35eb9f6d1ea0": {
        "unique_identifier": "a69fd0f7-ce06-492a-a49c-35eb9f6d1ea0",
        "person_name": "Maciej Stanuch",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Maciej Stanuch",
        "folder_name": "Maciej Stanuch",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Maciej Stanuch"
    },
    "20b7fd60-399b-44d8-ab63-8f87b53556e0": {
        "unique_identifier": "20b7fd60-399b-44d8-ab63-8f87b53556e0",
        "person_name": "Maciek Oleksy",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Maciek Oleksy",
        "folder_name": "Maciek Oleksy",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Maciek Oleksy"
    },
    "83a8a673-cacb-433c-a440-b9cfb7c64912": {
        "unique_identifier": "83a8a673-cacb-433c-a440-b9cfb7c64912",
        "person_name": "Marek Smerecki",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Marek Smerecki",
        "folder_name": "Marek Smerecki",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Marek Smerecki"
    },
    "91fbc8b5-6628-4e5f-a503-1f16b3cbda15": {
        "unique_identifier": "91fbc8b5-6628-4e5f-a503-1f16b3cbda15",
        "person_name": "Maria Biela zd. Kuziel",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Maria Biela zd. Kuziel",
        "folder_name": "Maria Biela zd. Kuziel",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Maria Biela zd. Kuziel"
    },
    "d2b66e8d-1c33-4f66-ab0a-46a3c6c30864": {
        "unique_identifier": "d2b66e8d-1c33-4f66-ab0a-46a3c6c30864",
        "person_name": "Maria Sławska zd. Kossowska",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Maria Sławska zd. Kossowska",
        "folder_name": "Maria Sławska zd. Kossowska",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Maria Sławska zd. Kossowska"
    },
    "e7573209-0c71-4e24-9a25-27093133ff33": {
        "unique_identifier": "e7573209-0c71-4e24-9a25-27093133ff33",
        "person_name": "Marian Srzednicki (1)",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Marian Srzednicki (1)",
        "folder_name": "Marian Srzednicki (1)",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Marian Srzednicki (1)"
    },
    "07089e49-a042-4dc4-9e2c-eab4f050362e": {
        "unique_identifier": "07089e49-a042-4dc4-9e2c-eab4f050362e",
        "person_name": "Marian Srzednicki (2)",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Marian Srzednicki (2)",
        "folder_name": "Marian Srzednicki (2)",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Marian Srzednicki (2)"
    },
    "54e5d39e-4a25-46bd-b1f4-85b0fdf7652f": {
        "unique_identifier": "54e5d39e-4a25-46bd-b1f4-85b0fdf7652f",
        "person_name": "Małgorzata (nieznane) zd.  Srzednicka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Małgorzata (nieznane) zd.  Srzednicka",
        "folder_name": "Małgorzata (nieznane) zd.  Srzednicka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Małgorzata (nieznane) zd.  Srzednicka"
    },
    "c71b2fea-f183-407b-bdb6-bbe95f5e252d": {
        "unique_identifier": "c71b2fea-f183-407b-bdb6-bbe95f5e252d",
        "person_name": "Mirosław Stanuch",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Mirosław Stanuch",
        "folder_name": "Mirosław Stanuch",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Mirosław Stanuch"
    },
    "0f362c19-9e30-4dae-9e7e-da52529e1c74": {
        "unique_identifier": "0f362c19-9e30-4dae-9e7e-da52529e1c74",
        "person_name": "Paweł Srzednicki",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Paweł Srzednicki",
        "folder_name": "Paweł Srzednicki",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Paweł Srzednicki"
    },
    "32367064-e2c8-4d67-9302-59842167ca57": {
        "unique_identifier": "32367064-e2c8-4d67-9302-59842167ca57",
        "person_name": "Piotrek Smerecki",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Piotrek Smerecki",
        "folder_name": "Piotrek Smerecki",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Piotrek Smerecki"
    },
    "7fccde66-95ca-4070-aeeb-af69c5cf1b3e": {
        "unique_identifier": "7fccde66-95ca-4070-aeeb-af69c5cf1b3e",
        "person_name": "Ryszarda Biela zd. Srzednicka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Ryszarda Biela zd. Srzednicka",
        "folder_name": "Ryszarda Biela zd. Srzednicka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Ryszarda Biela zd. Srzednicka"
    },
    "1c861ba7-5705-4ddb-8ce0-df34582daaf7": {
        "unique_identifier": "1c861ba7-5705-4ddb-8ce0-df34582daaf7",
        "person_name": "Sebastian Kuziel",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Sebastian Kuziel",
        "folder_name": "Sebastian Kuziel",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Sebastian Kuziel"
    },
    "f1e06f7d-6ffe-4fff-ab2a-397135848dd1": {
        "unique_identifier": "f1e06f7d-6ffe-4fff-ab2a-397135848dd1",
        "person_name": "Stanisława Srzednicka zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Stanisława Srzednicka zd. (nieznane)",
        "folder_name": "Stanisława Srzednicka zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Stanisława Srzednicka zd. (nieznane)"
    },
    "7bcde802-810d-43df-a435-2ff6245e4b6e": {
        "unique_identifier": "7bcde802-810d-43df-a435-2ff6245e4b6e",
        "person_name": "Stefania (nieznane) zd. Kuziel",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Stefania (nieznane) zd. Kuziel",
        "folder_name": "Stefania (nieznane) zd. Kuziel",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Stefania (nieznane) zd. Kuziel"
    },
    "def0221a-1737-45e1-9f64-a6c3dabac4a9": {
        "unique_identifier": "def0221a-1737-45e1-9f64-a6c3dabac4a9",
        "person_name": "Sylwia Zastawnik zd. Sternalska",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Sylwia Zastawnik zd. Sternalska",
        "folder_name": "Sylwia Zastawnik zd. Sternalska",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Sylwia Zastawnik zd. Sternalska"
    },
    "18ea5673-e708-40b6-b914-13991a4e39a3": {
        "unique_identifier": "18ea5673-e708-40b6-b914-13991a4e39a3",
        "person_name": "Sławomir Kaseja",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Sławomir Kaseja",
        "folder_name": "Sławomir Kaseja",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Sławomir Kaseja"
    },
    "00a72a6a-0555-4b23-8ad8-8a7167653c96": {
        "unique_identifier": "00a72a6a-0555-4b23-8ad8-8a7167653c96",
        "person_name": "Tomasz Kossowski",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Tomasz Kossowski",
        "folder_name": "Tomasz Kossowski",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Tomasz Kossowski"
    },
    "96730521-afa6-4401-badb-37ce13dcae1d": {
        "unique_identifier": "96730521-afa6-4401-badb-37ce13dcae1d",
        "person_name": "Tomasz Smerecki",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Tomasz Smerecki",
        "folder_name": "Tomasz Smerecki",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Tomasz Smerecki"
    },
    "c55651dd-ca80-47a9-934e-c7f5aeebf673": {
        "unique_identifier": "c55651dd-ca80-47a9-934e-c7f5aeebf673",
        "person_name": "Urszula Zamaria zd. Srzednicka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Urszula Zamaria zd. Srzednicka",
        "folder_name": "Urszula Zamaria zd. Srzednicka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Urszula Zamaria zd. Srzednicka"
    },
    "2689959d-c133-467a-bd15-c7300450e8ea": {
        "unique_identifier": "2689959d-c133-467a-bd15-c7300450e8ea",
        "person_name": "Wiktoria Kossowska zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Wiktoria Kossowska zd. (nieznane)",
        "folder_name": "Wiktoria Kossowska zd. (nieznane)",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Wiktoria Kossowska zd. (nieznane)"
    },
    "40c322c4-9b33-47a1-8fe4-698201844b72": {
        "unique_identifier": "40c322c4-9b33-47a1-8fe4-698201844b72",
        "person_name": "Witold Srzednicki",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Witold Srzednicki",
        "folder_name": "Witold Srzednicki",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Witold Srzednicki"
    },
    "31241ae5-7ec4-4426-b5f7-814c64cc0f67": {
        "unique_identifier": "31241ae5-7ec4-4426-b5f7-814c64cc0f67",
        "person_name": "Władysława (nieznane) zd. Kuziel",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Władysława (nieznane) zd. Kuziel",
        "folder_name": "Władysława (nieznane) zd. Kuziel",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Władysława (nieznane) zd. Kuziel"
    },
    "08c6d608-8224-4299-97eb-92ca96482960": {
        "unique_identifier": "08c6d608-8224-4299-97eb-92ca96482960",
        "person_name": "Zofia (nieznane) zd. Kuziel",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Zofia (nieznane) zd. Kuziel",
        "folder_name": "Zofia (nieznane) zd. Kuziel",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Zofia (nieznane) zd. Kuziel"
    },
    "ec0b5ba7-3ef0-40e8-b5f0-b9050fe72bef": {
        "unique_identifier": "ec0b5ba7-3ef0-40e8-b5f0-b9050fe72bef",
        "person_name": "Zofia Stanuch zd. Srzednicka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Zofia Stanuch zd. Srzednicka",
        "folder_name": "Zofia Stanuch zd. Srzednicka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Zofia Stanuch zd. Srzednicka"
    },
    "1134504b-feb5-4cc5-bd81-02d1ab5c1b8f": {
        "unique_identifier": "1134504b-feb5-4cc5-bd81-02d1ab5c1b8f",
        "person_name": "Łucja Srzednicka",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Łucja Srzednicka",
        "folder_name": "Łucja Srzednicka",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Łucja Srzednicka"
    },
    "9038ba49-f536-4193-ad3e-06be2c706a80": {
        "unique_identifier": "9038ba49-f536-4193-ad3e-06be2c706a80",
        "person_name": "Łukasz Sternalski",
        "location": "C:\\Sorted tree\\People\\Srzednicki\\Łukasz Sternalski",
        "folder_name": "Łukasz Sternalski",
        "folder_path": "C:\\Sorted tree\\People\\Srzednicki\\Łukasz Sternalski"
    },
    "069bfffe-54c2-4e09-96bc-8620b93af36a": {
        "unique_identifier": "069bfffe-54c2-4e09-96bc-8620b93af36a",
        "person_name": "(nieznane) (nieznane)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) (nieznane) (mężczyzna)",
        "folder_name": "(nieznane) (nieznane) (mężczyzna)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) (nieznane) (mężczyzna)"
    },
    "3b683232-784d-4a17-8577-a8e8ea0fcc69": {
        "unique_identifier": "3b683232-784d-4a17-8577-a8e8ea0fcc69",
        "person_name": "(nieznane) (nieznane) zd. (nieznane)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) (nieznane) zd. (nieznane) - żona Stanisława Gładysza(2)",
        "folder_name": "(nieznane) (nieznane) zd. (nieznane) - żona Stanisława Gładysza(2)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) (nieznane) zd. (nieznane) - żona Stanisława Gładysza(2)"
    },
    "2a611de4-ed75-4785-b483-c7ef784e5258": {
        "unique_identifier": "2a611de4-ed75-4785-b483-c7ef784e5258",
        "person_name": "(nieznane) (nieznane) zd. Paziewska",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) (nieznane) zd. Paziewska",
        "folder_name": "(nieznane) (nieznane) zd. Paziewska",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) (nieznane) zd. Paziewska"
    },
    "509b4f9e-2ba5-4be4-8bd2-b3621c376915": {
        "unique_identifier": "509b4f9e-2ba5-4be4-8bd2-b3621c376915",
        "person_name": "(nieznane) (nieznane) zd. Wasilewska",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) (nieznane) zd. Wasilewska",
        "folder_name": "(nieznane) (nieznane) zd. Wasilewska",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) (nieznane) zd. Wasilewska"
    },
    "79dc0c67-7f72-4dbf-952f-d43e907e3127": {
        "unique_identifier": "79dc0c67-7f72-4dbf-952f-d43e907e3127",
        "person_name": "(nieznane) Cwyl",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Cwyl",
        "folder_name": "(nieznane) Cwyl",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Cwyl"
    },
    "de477f33-c9d4-4bb3-9d19-1b367bf68d1d": {
        "unique_identifier": "de477f33-c9d4-4bb3-9d19-1b367bf68d1d",
        "person_name": "(nieznane) Gładysz",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Gładysz",
        "folder_name": "(nieznane) Gładysz",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Gładysz"
    },
    "23d422fc-cf61-421a-a4ad-bd38ce79d128": {
        "unique_identifier": "23d422fc-cf61-421a-a4ad-bd38ce79d128",
        "person_name": "(nieznane) Małecki (1)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Małecki (1)",
        "folder_name": "(nieznane) Małecki (1)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Małecki (1)"
    },
    "4d89772d-2ab9-454f-bee0-95b702d4609c": {
        "unique_identifier": "4d89772d-2ab9-454f-bee0-95b702d4609c",
        "person_name": "(nieznane) Małecki (2)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Małecki (2)",
        "folder_name": "(nieznane) Małecki (2)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Małecki (2)"
    },
    "c6429b58-2a0a-4906-bc16-e91ad079516b": {
        "unique_identifier": "c6429b58-2a0a-4906-bc16-e91ad079516b",
        "person_name": "(nieznane) Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Staluszka",
        "folder_name": "(nieznane) Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Staluszka"
    },
    "51a37079-a74b-4c1b-bf78-d9e84b2599e6": {
        "unique_identifier": "51a37079-a74b-4c1b-bf78-d9e84b2599e6",
        "person_name": "(nieznane) Staluszka zd. (nieznane) (1)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Staluszka zd. (nieznane) (1)",
        "folder_name": "(nieznane) Staluszka zd. (nieznane) (1)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Staluszka zd. (nieznane) (1)"
    },
    "a2d65716-59c2-4ec0-a00a-1980a64aac06": {
        "unique_identifier": "a2d65716-59c2-4ec0-a00a-1980a64aac06",
        "person_name": "(nieznane) Staluszka zd. (nieznane) (2)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Staluszka zd. (nieznane) (2)",
        "folder_name": "(nieznane) Staluszka zd. (nieznane) (2)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Staluszka zd. (nieznane) (2)"
    },
    "55391c17-7676-4ac6-bca4-d9b433f13ce4": {
        "unique_identifier": "55391c17-7676-4ac6-bca4-d9b433f13ce4",
        "person_name": "(nieznane) Wasilewska zd. Gładysz",
        "location": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Wasilewska zd. Gładysz",
        "folder_name": "(nieznane) Wasilewska zd. Gładysz",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\(nieznane) Wasilewska zd. Gładysz"
    },
    "a3c1db7c-56be-4cc6-9215-2f6be3d39a3b": {
        "unique_identifier": "a3c1db7c-56be-4cc6-9215-2f6be3d39a3b",
        "person_name": "Adela Cwyl zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Adela Cwyl zd. Staluszka",
        "folder_name": "Adela Cwyl zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Adela Cwyl zd. Staluszka"
    },
    "99adab85-0d31-4542-b174-d1c89d0dd556": {
        "unique_identifier": "99adab85-0d31-4542-b174-d1c89d0dd556",
        "person_name": "Andrzej Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Andrzej Staluszka",
        "folder_name": "Andrzej Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Andrzej Staluszka"
    },
    "4aebd83b-b1f9-497d-87ed-a45229076571": {
        "unique_identifier": "4aebd83b-b1f9-497d-87ed-a45229076571",
        "person_name": "Aniela (nieznane) zd. Cwyl",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Aniela (nieznane) zd. Cwyl",
        "folder_name": "Aniela (nieznane) zd. Cwyl",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Aniela (nieznane) zd. Cwyl"
    },
    "f9105a32-998f-428c-85a0-a9b95618f759": {
        "unique_identifier": "f9105a32-998f-428c-85a0-a9b95618f759",
        "person_name": "Antonina Hys zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Antonina Hys zd. Staluszka",
        "folder_name": "Antonina Hys zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Antonina Hys zd. Staluszka"
    },
    "c9b1ed62-f34d-401a-9521-4967ec72a6f7": {
        "unique_identifier": "c9b1ed62-f34d-401a-9521-4967ec72a6f7",
        "person_name": "Arkadiusz Hołubek",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Arkadiusz Hołubek",
        "folder_name": "Arkadiusz Hołubek",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Arkadiusz Hołubek"
    },
    "bbebae94-9786-4e8a-ae78-ca9e84405ec6": {
        "unique_identifier": "bbebae94-9786-4e8a-ae78-ca9e84405ec6",
        "person_name": "Bronisław Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Bronisław Staluszka",
        "folder_name": "Bronisław Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Bronisław Staluszka"
    },
    "11c03130-40ae-4e46-8d0a-849e49947c46": {
        "unique_identifier": "11c03130-40ae-4e46-8d0a-849e49947c46",
        "person_name": "Bronisława (nieznane) zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Bronisława (nieznane) zd. Staluszka",
        "folder_name": "Bronisława (nieznane) zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Bronisława (nieznane) zd. Staluszka"
    },
    "a49cbc4c-19b8-4385-9691-4f46f32379e1": {
        "unique_identifier": "a49cbc4c-19b8-4385-9691-4f46f32379e1",
        "person_name": "Franciszek Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Franciszek Staluszka",
        "folder_name": "Franciszek Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Franciszek Staluszka"
    },
    "afca1dbd-66c1-48e7-95a7-cb2a6b97b43c": {
        "unique_identifier": "afca1dbd-66c1-48e7-95a7-cb2a6b97b43c",
        "person_name": "Franciszka Staluszka zd. Bogucka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Franciszka Staluszka zd. Bogucka",
        "folder_name": "Franciszka Staluszka zd. Bogucka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Franciszka Staluszka zd. Bogucka"
    },
    "df6ee577-dca5-470f-8bc4-42982c4cc621": {
        "unique_identifier": "df6ee577-dca5-470f-8bc4-42982c4cc621",
        "person_name": "Genowefa Mańturzyk zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Genowefa Mańturzyk zd. Staluszka",
        "folder_name": "Genowefa Mańturzyk zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Genowefa Mańturzyk zd. Staluszka"
    },
    "5b5475ba-09b5-4fee-9786-165b5bb5d024": {
        "unique_identifier": "5b5475ba-09b5-4fee-9786-165b5bb5d024",
        "person_name": "Ignacy Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Ignacy Staluszka",
        "folder_name": "Ignacy Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Ignacy Staluszka"
    },
    "34b08ef2-9f13-47f7-bbda-3e9b73a3186d": {
        "unique_identifier": "34b08ef2-9f13-47f7-bbda-3e9b73a3186d",
        "person_name": "Inga Szubert zd. Hołubek",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Inga Szubert zd. Hołubek",
        "folder_name": "Inga Szubert zd. Hołubek",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Inga Szubert zd. Hołubek"
    },
    "3a88cc69-5fc4-4a54-ad93-d2b1c7bf8d33": {
        "unique_identifier": "3a88cc69-5fc4-4a54-ad93-d2b1c7bf8d33",
        "person_name": "Izabela (nieznane) zd. Hołubek",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Izabela (nieznane) zd. Hołubek",
        "folder_name": "Izabela (nieznane) zd. Hołubek",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Izabela (nieznane) zd. Hołubek"
    },
    "3f6aee11-7571-4ec8-b55e-e5660af2a4e4": {
        "unique_identifier": "3f6aee11-7571-4ec8-b55e-e5660af2a4e4",
        "person_name": "Jadwiga Mankin zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Jadwiga Mankin zd. Staluszka",
        "folder_name": "Jadwiga Mankin zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Jadwiga Mankin zd. Staluszka"
    },
    "89103011-0749-40ea-b119-82afc7e0981e": {
        "unique_identifier": "89103011-0749-40ea-b119-82afc7e0981e",
        "person_name": "Jan Gładysz",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Jan Gładysz",
        "folder_name": "Jan Gładysz",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Jan Gładysz"
    },
    "e964ac2c-ad02-4816-a841-443f4f06b2ba": {
        "unique_identifier": "e964ac2c-ad02-4816-a841-443f4f06b2ba",
        "person_name": "Jan Wasilewski",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Jan Wasilewski",
        "folder_name": "Jan Wasilewski",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Jan Wasilewski"
    },
    "15898648-e08e-4ea9-ad7c-eb774ee3428b": {
        "unique_identifier": "15898648-e08e-4ea9-ad7c-eb774ee3428b",
        "person_name": "Janina (nieznane) zd. Gładysz",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Janina (nieznane) zd. Gładysz",
        "folder_name": "Janina (nieznane) zd. Gładysz",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Janina (nieznane) zd. Gładysz"
    },
    "10e82fcf-515c-45da-87bd-7573cc446321": {
        "unique_identifier": "10e82fcf-515c-45da-87bd-7573cc446321",
        "person_name": "Janina Szydłowska zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Janina Szydłowska zd. Staluszka",
        "folder_name": "Janina Szydłowska zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Janina Szydłowska zd. Staluszka"
    },
    "665080f3-1d30-4581-b543-a97fc68a12ef": {
        "unique_identifier": "665080f3-1d30-4581-b543-a97fc68a12ef",
        "person_name": "Jerzy Hołubek",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Jerzy Hołubek",
        "folder_name": "Jerzy Hołubek",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Jerzy Hołubek"
    },
    "8317b106-c52f-4ce7-be81-faf88063314c": {
        "unique_identifier": "8317b106-c52f-4ce7-be81-faf88063314c",
        "person_name": "Julianna Staluszka zd. Paziewska",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Julianna Staluszka zd. Paziewska",
        "folder_name": "Julianna Staluszka zd. Paziewska",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Julianna Staluszka zd. Paziewska"
    },
    "5a863a8d-7fd8-4531-a0a9-1908bb69e27a": {
        "unique_identifier": "5a863a8d-7fd8-4531-a0a9-1908bb69e27a",
        "person_name": "Józef Mańturzyk",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Józef Mańturzyk",
        "folder_name": "Józef Mańturzyk",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Józef Mańturzyk"
    },
    "854e6aa8-2392-4840-9c32-f4e86a47b515": {
        "unique_identifier": "854e6aa8-2392-4840-9c32-f4e86a47b515",
        "person_name": "Józefa Małecka zd. Gładysz",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Józefa Małecka zd. Gładysz",
        "folder_name": "Józefa Małecka zd. Gładysz",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Józefa Małecka zd. Gładysz"
    },
    "ba75549e-99df-4d6f-8382-84475ac6075c": {
        "unique_identifier": "ba75549e-99df-4d6f-8382-84475ac6075c",
        "person_name": "Józefa Staluszka zd. Szeląg",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Józefa Staluszka zd. Szeląg",
        "folder_name": "Józefa Staluszka zd. Szeląg",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Józefa Staluszka zd. Szeląg"
    },
    "b1d80314-7cd4-4233-b5b1-db4d93281da7": {
        "unique_identifier": "b1d80314-7cd4-4233-b5b1-db4d93281da7",
        "person_name": "Leokadia Markowska zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Leokadia Markowska zd. Staluszka",
        "folder_name": "Leokadia Markowska zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Leokadia Markowska zd. Staluszka"
    },
    "70486b29-3ba5-4499-8750-b07663996d6e": {
        "unique_identifier": "70486b29-3ba5-4499-8750-b07663996d6e",
        "person_name": "Marcin Staluszka (1)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Marcin Staluszka (1)",
        "folder_name": "Marcin Staluszka (1)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Marcin Staluszka (1)"
    },
    "235cf2a1-ef03-4b19-b4a6-b5582a1b5f2f": {
        "unique_identifier": "235cf2a1-ef03-4b19-b4a6-b5582a1b5f2f",
        "person_name": "Marcin Staluszka (2)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Marcin Staluszka (2)",
        "folder_name": "Marcin Staluszka (2)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Marcin Staluszka (2)"
    },
    "2c7c9436-ae8e-44c2-8d43-848197b29e36": {
        "unique_identifier": "2c7c9436-ae8e-44c2-8d43-848197b29e36",
        "person_name": "Maria Dębek zd. Gładysz",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Maria Dębek zd. Gładysz",
        "folder_name": "Maria Dębek zd. Gładysz",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Maria Dębek zd. Gładysz"
    },
    "5b51db1d-254e-4b25-b320-fab4cad7e06a": {
        "unique_identifier": "5b51db1d-254e-4b25-b320-fab4cad7e06a",
        "person_name": "Maria Hołubek zd. Mańturzyk",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Maria Hołubek zd. Mańturzyk",
        "folder_name": "Maria Hołubek zd. Mańturzyk",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Maria Hołubek zd. Mańturzyk"
    },
    "aa21e4f1-3e7e-492f-b994-f6a508210837": {
        "unique_identifier": "aa21e4f1-3e7e-492f-b994-f6a508210837",
        "person_name": "Marianna (nieznane) zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Marianna (nieznane) zd. Staluszka",
        "folder_name": "Marianna (nieznane) zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Marianna (nieznane) zd. Staluszka"
    },
    "38e4d3b7-82f5-4e0d-8f5a-be5b52413c22": {
        "unique_identifier": "38e4d3b7-82f5-4e0d-8f5a-be5b52413c22",
        "person_name": "Marianna Gładysz zd. Paziewska",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Marianna Gładysz zd. Paziewska",
        "folder_name": "Marianna Gładysz zd. Paziewska",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Marianna Gładysz zd. Paziewska"
    },
    "e024410d-eb89-4984-9f85-100c38c67007": {
        "unique_identifier": "e024410d-eb89-4984-9f85-100c38c67007",
        "person_name": "Marianna Mroczek zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Marianna Mroczek zd. Staluszka",
        "folder_name": "Marianna Mroczek zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Marianna Mroczek zd. Staluszka"
    },
    "381e40d5-e657-4826-a6ab-f8f8ed3ad175": {
        "unique_identifier": "381e40d5-e657-4826-a6ab-f8f8ed3ad175",
        "person_name": "Małgorzata Staluszka zd. Gładysz",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Małgorzata Staluszka zd. Gładysz",
        "folder_name": "Małgorzata Staluszka zd. Gładysz",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Małgorzata Staluszka zd. Gładysz"
    },
    "7f51c205-9ac1-49b0-8c4f-5aaf4687a565": {
        "unique_identifier": "7f51c205-9ac1-49b0-8c4f-5aaf4687a565",
        "person_name": "Piotr Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Piotr Staluszka",
        "folder_name": "Piotr Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Piotr Staluszka"
    },
    "50c5dbbe-aca7-48f0-9157-93957a38fad6": {
        "unique_identifier": "50c5dbbe-aca7-48f0-9157-93957a38fad6",
        "person_name": "Robert Hołubek",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Robert Hołubek",
        "folder_name": "Robert Hołubek",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Robert Hołubek"
    },
    "f7443bc4-12d9-42a0-b76f-9d6aa7141220": {
        "unique_identifier": "f7443bc4-12d9-42a0-b76f-9d6aa7141220",
        "person_name": "Roman Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Roman Staluszka",
        "folder_name": "Roman Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Roman Staluszka"
    },
    "9d84ce83-2f37-4189-acfb-d664d4417aab": {
        "unique_identifier": "9d84ce83-2f37-4189-acfb-d664d4417aab",
        "person_name": "Stanisław Cwyl",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Cwyl",
        "folder_name": "Stanisław Cwyl",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Cwyl"
    },
    "3b4d9a4a-38c3-4fa6-adad-4b42fee0abf0": {
        "unique_identifier": "3b4d9a4a-38c3-4fa6-adad-4b42fee0abf0",
        "person_name": "Stanisław Gładysz (1)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Gładysz (1)",
        "folder_name": "Stanisław Gładysz (1)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Gładysz (1)"
    },
    "ebb492e9-5257-498d-bb82-555334872a40": {
        "unique_identifier": "ebb492e9-5257-498d-bb82-555334872a40",
        "person_name": "Stanisław Gładysz (2)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Gładysz (2)",
        "folder_name": "Stanisław Gładysz (2)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Gładysz (2)"
    },
    "53f7781b-1598-4d75-83bd-26bcf3bce578": {
        "unique_identifier": "53f7781b-1598-4d75-83bd-26bcf3bce578",
        "person_name": "Stanisław Mroczek",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Mroczek",
        "folder_name": "Stanisław Mroczek",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Mroczek"
    },
    "68fe6a0f-f30e-47df-93e6-09c8abf1ae70": {
        "unique_identifier": "68fe6a0f-f30e-47df-93e6-09c8abf1ae70",
        "person_name": "Stanisław Staluszka (1)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Staluszka (1)",
        "folder_name": "Stanisław Staluszka (1)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Staluszka (1)"
    },
    "50e2e400-6a20-423c-afa8-93534e8e761d": {
        "unique_identifier": "50e2e400-6a20-423c-afa8-93534e8e761d",
        "person_name": "Stanisław Staluszka (2)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Staluszka (2)",
        "folder_name": "Stanisław Staluszka (2)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Stanisław Staluszka (2)"
    },
    "7acb1b8e-935c-4bef-859a-1103d2be76bb": {
        "unique_identifier": "7acb1b8e-935c-4bef-859a-1103d2be76bb",
        "person_name": "Stanisława (nieznane) zd. Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Stanisława (nieznane) zd. Staluszka",
        "folder_name": "Stanisława (nieznane) zd. Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Stanisława (nieznane) zd. Staluszka"
    },
    "f573bd6d-fcc0-4d2f-8d8a-c1476e390c0b": {
        "unique_identifier": "f573bd6d-fcc0-4d2f-8d8a-c1476e390c0b",
        "person_name": "Wacław Mańturzyk",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Wacław Mańturzyk",
        "folder_name": "Wacław Mańturzyk",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Wacław Mańturzyk"
    },
    "c02d04f0-03f8-4475-b7cb-f9b8a4587255": {
        "unique_identifier": "c02d04f0-03f8-4475-b7cb-f9b8a4587255",
        "person_name": "Wacław Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Wacław Staluszka",
        "folder_name": "Wacław Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Wacław Staluszka"
    },
    "3db4c268-9d8f-4669-879c-bfc1056aeb4b": {
        "unique_identifier": "3db4c268-9d8f-4669-879c-bfc1056aeb4b",
        "person_name": "Witold Staluszka",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Witold Staluszka",
        "folder_name": "Witold Staluszka",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Witold Staluszka"
    },
    "faf82ba4-68df-41c1-9ba2-fc959cf032d0": {
        "unique_identifier": "faf82ba4-68df-41c1-9ba2-fc959cf032d0",
        "person_name": "Władysław Staluszka (1)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (1)",
        "folder_name": "Władysław Staluszka (1)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (1)"
    },
    "21770239-bea5-4aeb-a531-97fda6d5e804": {
        "unique_identifier": "21770239-bea5-4aeb-a531-97fda6d5e804",
        "person_name": "Władysław Staluszka (2)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (2)",
        "folder_name": "Władysław Staluszka (2)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (2)"
    },
    "3bd81d72-4448-4fdf-ba93-556b0d50783c": {
        "unique_identifier": "3bd81d72-4448-4fdf-ba93-556b0d50783c",
        "person_name": "Władysław Staluszka (3)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (3)",
        "folder_name": "Władysław Staluszka (3)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (3)"
    },
    "760c7387-d98e-434d-ac5f-f7cef08808e0": {
        "unique_identifier": "760c7387-d98e-434d-ac5f-f7cef08808e0",
        "person_name": "Władysław Staluszka (4)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (4)",
        "folder_name": "Władysław Staluszka (4)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (4)"
    },
    "8cd5185b-dc09-4bf7-8111-436d2e5d404f": {
        "unique_identifier": "8cd5185b-dc09-4bf7-8111-436d2e5d404f",
        "person_name": "Władysław Staluszka (5)",
        "location": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (5)",
        "folder_name": "Władysław Staluszka (5)",
        "folder_path": "C:\\Sorted tree\\People\\Staluszka\\Władysław Staluszka (5)"
    }
}

# List of folders with non-conforming names (not 2-9 words)
NON_CONFORMING_FOLDERS: List[str] = []
