from abc import ABC, abstractmethod
import json
from enum import Enum
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree


class Genre(Enum):
    """Исчисляемый класс жанров"""


class TrackGenre(Genre):
    ROCK = "rock"
    POP = "pop"
    HIP_HOP = "hip-hop"
    ELECTRONIC = "electronic"
    CLASSIC = "classic"


class AudioBookGenre(Genre):
    COMEDY = "comedy"
    HORROR = "horror"
    TRILLER = "triller"
    ROMAN = "roman"
    NOVELL = "novell"


class Permission(Enum):
    VIEW_USERS = "view_users"
    EDIT_USERS = "edit_users"
    BAN_USERS = "ban_users"
    USE_PLAYGROUND = "use_playground"
    INVITE_ADMINS = "invite_admins"

    @classmethod
    def all(cls) -> list['Permission']:
        return list(cls)


class Serializable(ABC):
    """Абстрактный класс сериализуемых объектов"""

    @abstractmethod
    def serialize(self):
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, data: Dict[str, Any]):
        pass


class BaseSmartSerializableModel(Serializable):
    """Базовый класс сериализуемых объектов с умной сериализацией"""

    _id_field: str = "id"

    @property
    def id(self):
        return getattr(self, self._id_field)

    def serialize(self):
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, BaseSmartSerializableModel):
                result[key] = value.id
            elif isinstance(value, Enum):
                result[key] = value.value
            elif isinstance(value, list):
                result[key] = [
                    v.id if isinstance(v, BaseSmartSerializableModel) else v for v in value
                ]
            else:
                result[key] = value
        return result

    @classmethod
    def deserialize(cls, data: Dict[str, Any], lookup: Dict[str, 'BaseSmartSerializableModel'] = None):
        kwargs = {}

        for key, value in data.items():
            if lookup and isinstance(value, str) and value in lookup:
                kwargs[key] = lookup[value]
            elif lookup and isinstance(value, list):
                kwargs[key] = [
                    lookup[v] if isinstance(v, str) and v in lookup else v
                    for v in value
                ]
            elif isinstance(value, str) and key == "genre":
                kwargs[key] = Genre(value)
            else:
                kwargs[key] = value

        return cls(**kwargs)


class FileHandler(ABC):
    @abstractmethod
    def save(self, data: List[Serializable], filename: str):
        pass

    @classmethod
    @abstractmethod
    def load(cls, filename: str) -> List[Dict[str, Any]]:
        pass


class FileFormats(Enum):
    JSON = "json"
    XML = "xml"


class JSONFileHandler(FileHandler):
    def save(self, data: List[Serializable], filename: str):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump([item.serialize() for item in data], f, indent=2, ensure_ascii=False)

    def load(self, filename: str) -> List[Dict[str, Any]]:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)


class XMLFileHandler(FileHandler):
    def save(self, data: List[Serializable], filename: str):
        root = ElementTree.Element("data")
        for item in data:
            item_element = ElementTree.SubElement(root, "item")
            for key, value in item.serialize().items():
                child = ElementTree.SubElement(item_element, key)
                if isinstance(value, list):
                    child.text = ",".join(str(v) for v in value)
                else:
                    child.text = str(value)

        tree = ElementTree.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def load(self, filename: str) -> List[Dict[str, Any]]:
        tree = ElementTree.parse(filename)
        root = tree.getroot()

        result = []
        for item_element in root.findall("item"):
            item_data = {}
            for child in item_element:
                if child.text and "," in child.text:
                    item_data[child.tag] = child.text.split(",")
                else:
                    item_data[child.tag] = child.text
            result.append(item_data)

        return result


class FileHandlerSelector:
    @staticmethod
    def get_handler(format: FileFormats) -> FileHandler:
        handlers = {
            FileFormats.JSON: JSONFileHandler(),
            FileFormats.XML: XMLFileHandler()
        }

        return handlers.get(format)


class DataSerializer:
    @staticmethod
    def save(filename: str, objects: List[Serializable], format: str):
        pass

    @staticmethod
    def load(filename: str, classes: List[type[Serializable]], format: str):
        pass


class SmartDataSerializer(DataSerializer):
    @staticmethod
    def save(filename: str, objects: List[BaseSmartSerializableModel], format: str):
        handler = FileHandlerSelector.get_handler(format)
        handler.save(objects, filename)

        print(f"✅ Данные сохранены в {filename}")

    @staticmethod
    def load(filename: str, classes: List[type[BaseSmartSerializableModel]], format: str):
        handler = FileHandlerSelector.get_handler(format)
        data = handler.load(filename)

        print(f"📄 Загружено {len(data)} записей")

        lookup = {}

        for obj_data in data:
            for cls in classes:
                if cls._id_field in obj_data:
                    instance = cls.deserialize(obj_data)
                    lookup[instance.id] = instance
                    break

        for obj_data in data:
            for cls in classes:
                if cls._id_field in obj_data:
                    instance = cls.deserialize(obj_data, lookup)
                    lookup[instance.id] = instance
                    break

        return lookup


class User(BaseSmartSerializableModel):
    _id_field: str = "user_id"

    def __init__(self, user_id: str, name: str, email: str, subscribed: bool,
                 playlists: Optional[List['Playlist']] = None, favourite_tracks: Optional[List['Track']] = None,
                 favourite_albums: Optional[List['Album']] = None, favourite_artists: Optional[List['Artist']] = None):
        self.__user_id = user_id
        self.__name = name
        self.__email = email
        self.__subscribed = subscribed

        self.__playlists = playlists or []
        self.__favourite_tracks = favourite_tracks or []
        self.__favourite_albums = favourite_albums or []
        self.__favourite_artists = favourite_artists or []


class Artist(User):
    _id_field: str = "artist_id"

    def __init__(self, artist_id: str, name: str, email: str,
                 tracks: Optional[List['Track']] = None, albums: Optional[List['Album']] = None):
        super().__init__(artist_id, name, email, subscribed=True)

        self.__tracks = tracks or []
        self.__albums = albums or []


class Admin(User):
    def __init__(self, user_id: str, name: str, email: str, permissions: Optional[List[Permission]] = None):
        super().__init__(user_id, name, email, subscribed=True)

        self.__permissions = permissions or []


class Collection(BaseSmartSerializableModel):
    _id_field: str = "collection_id"

    def __init__(self, collection_id: str, title: str, contents: List['Content'],
                 author: User, collaborators: Optional[List[User]] = None):
        self.__collection_id = collection_id
        self.__title = title
        self.__contents = contents
        self.__author  = author

        self.__collaborators = collaborators or []


class Album(Collection):
    def __init__(self, album_id: str, title: str, tracks: List['Track'],
                 artist: Artist, collaborators: Optional[List[Artist]] = None):
        super().__init__(album_id, title, tracks, artist, collaborators)


class Playlist(Collection):
    def __init__(self, playlist_id: str, title: str, tracks: List['Track'], owner: User):
        super().__init__(playlist_id, title, tracks, owner)


class AudioBook(Collection):
    def __init__(self, audio_book_id: str, title: str, chapters: List['AudioBookChapter'], author: Artist):
        super().__init__(audio_book_id, title, chapters, author)


class Content(BaseSmartSerializableModel):
    _id_field: str = "content_id"

    def __init__(self, content_id: str, title: str, genres: List[Genre], artist: Artist,
                 collaborators: Optional[List[Artist]] = None, source: Optional[Collection] = None):
        self.__content_id = content_id
        self.__title = title

        self.__genres = genres

        self.__artist = artist

        self.__collaborators = collaborators or []

        self.__source = source


class Track(Content):
    def __init__(self, track_id: str, title: str, genres: List[TrackGenre], artist: Artist,
                 collaborators: Optional[List[Artist]] = None, producers: Optional[List[Artist]] = None,
                 album: Optional[Album] = None):
        super().__init__(track_id, title, genres, artist, collaborators, album)

        self.__producers = producers or []


class AudioBookChapter(Content):
    def __init__(self, chapter_id: str, title: str, genres: List[AudioBookGenre], author: Artist,
                 collaborators: Optional[List[Artist]] = None, audio_book: Optional[Collection] = None,
                 narrators: Optional[List[Artist]] = None):
        super().__init__(chapter_id, title, genres, author, collaborators, audio_book)

        self.__narrators = narrators or [author]


class MusicPlayer(BaseSmartSerializableModel):
    _id_field: str = "music_player_id"

    def __init(self, music_player_id: str, user: User):
        self.__music_player_id = music_player_id
        self.__user = user

        self.__current_track: Optional[Track] = None
        self.__current_playlist: Optional[Playlist] = None

        self.__is_playing: bool = False

        self.__volume: float = 0.8
        self.__current_track_position: float = 0.0

        self.__shuffle_mode: bool = False
        self.__repeat_mode: str = "none"
        self.__playback_speed: float = 1.0
        self.__equalizer_settings: dict[str, float] = {}

        self.__history: list[Track] = []


if __name__ == "__main__":
    pass
