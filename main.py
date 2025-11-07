from abc import ABC, abstractmethod
import json
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import timedelta
from xml.etree import ElementTree
import xml.dom.minidom as minidom
import time
import random

from config import DEFAULT_FILE_INDENT, MUSIC_PLAYER_PREFIX
from errors import DataError, EmptyValueError, InvalidTypeError, CustomIndexError
from utils import validate_str, validate_list


class TrackGenre(Enum):
    """Перечисляемый класс, описывающий жанры треков"""

    ROCK = "rock"
    POP = "pop"
    HIP_HOP = "hip-hop"
    ELECTRONIC = "electronic"
    CLASSIC = "classic"


class AudioBookGenre(Enum):
    """Перечисляемый класс, описывающий жанры аудиокниг"""

    COMEDY = "comedy"
    HORROR = "horror"
    TRILLER = "triller"
    ROMAN = "roman"
    NOVELL = "novell"


class Permission(Enum):
    """Перечисляемый класс, описывающий привилегии администратора"""

    VIEW_USERS = "view_users"
    EDIT_USERS = "edit_users"
    BAN_USERS = "ban_users"
    SEE_ANALYTICS = "see_analytics"
    INVITE_ADMINS = "invite_admins"


    @classmethod
    def all(cls) -> list['Permission']:
        return list(cls)


class Serializable(ABC):
    """Абстрактный класс, описывающий сериализуемые объекты"""

    @abstractmethod
    def serialize(self):
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, data: Dict[str, Any]):
        pass


class FileHandler(ABC):
    """
    Абстрактный класс, описывающий обработчик файлов

    Можно сохранять данные в файл и выгружать их из файла
    """

    @abstractmethod
    def save(self, data: List[Serializable], filename: str):
        pass

    @classmethod
    @abstractmethod
    def load(cls, filename: str) -> List[Dict[str, Any]]:
        pass


class JSONFileHandler(FileHandler):
    """Класс, описывающий обработчик файлов .JSON"""

    def save(self, data: List[Serializable], filename: str):
        with open(filename, "w", encoding="utf-8") as file:
            json.dump([item.serialize() for item in data], file, indent=DEFAULT_FILE_INDENT, ensure_ascii=False)


    def load(self, filename: str) -> List[Dict[str, Any]]:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)


class XMLFileHandler(FileHandler):
    """Класс, описывающий обработчик файлов .XML"""

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

        tree = ElementTree.tostring(root, encoding="utf-8")
        decorated_tree = minidom.parseString(tree).toprettyxml(indent=" " * DEFAULT_FILE_INDENT)

        with open(filename, "w", encoding="utf-8") as file:
            file.write(decorated_tree)

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


class Person(Serializable):
    """Базовый класс, описывающий человека в системе"""

    def __init__(self, person_id: str, name: str, email: str):
        self._person_id = person_id
        self._name = name
        self._email = email

    def __str__(self):
        return (
            f"ID: {self._person_id}\n"
            f"Имя: {self._name}\n"
            f"Почта: {self._email}\n"
        )

    @property
    def person_id(self) -> str:
        return self._person_id

    @person_id.setter
    def person_id(self, value: str):
        if not isinstance(value, str):
            raise InvalidTypeError("person_id", "str", type(value).__name__)
        if not value.strip():
            raise EmptyValueError("person_id")
        self._person_id = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        validate_str(value, "name")
        self._name = value

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str):
        validate_str(value, "email")

        if "@" not in value or "." not in value.split("@")[-1]:
            raise DataError(f"Некорректный адрес электронной почты: \"{value}\"")

        self._email = value

    def serialize(self) -> Dict[str, Any]:
        return {
            "id": self._person_id,
            "name": self._name,
            "email": self._email
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Person':
        return cls(
            person_id=data["id"],
            name=data["name"],
            email=data["email"]
        )


class User(Person):
    """Класс, описывающий пользователя"""

    def __init__(self, user_id: str, name: str, email: str, subscribed: bool,
                 playlists: Optional[List['Playlist']] = None, favourite_tracks: Optional[List['Track']] = None,
                 favourite_albums: Optional[List['Album']] = None, favourite_artists: Optional[List['Artist']] = None):
        super().__init__(user_id, name, email)

        self._subscribed = subscribed

        self._playlists = playlists or []
        self._favourite_tracks = favourite_tracks or []
        self._favourite_albums = favourite_albums or []
        self._favourite_artists = favourite_artists or []

    @property
    def user_id(self) -> str:
        return self.person_id

    @property
    def subscribed(self) -> bool:
        return self._subscribed

    @subscribed.setter
    def subscribed(self, value: bool):
        if not isinstance(value, bool):
            raise InvalidTypeError("subscribed", "bool", type(value).__name__)
        self._subscribed = value

    @property
    def playlists(self) -> List['Playlist']:
        return self._playlists.copy()

    @playlists.setter
    def playlists(self, value: List['Playlist']):
        validate_list(value, "playlists", Playlist)

        self._playlists = value

    @property
    def favourite_tracks(self) -> List['Track']:
        return self._favourite_tracks.copy()

    @favourite_tracks.setter
    def favourite_tracks(self, value: List['Track']):
        validate_list(value, "favourite_tracks", Track)

        self._favourite_tracks = value

    @property
    def favourite_albums(self) -> List['Album']:
        return self._favourite_albums.copy()

    @favourite_albums.setter
    def favourite_albums(self, value: List['Album']):
        validate_list(value, "favourite_albums", Album)

        self._favourite_albums = value

    @property
    def favourite_artists(self) -> List['Artist']:
        return self._favourite_artists.copy()

    @favourite_artists.setter
    def favourite_artists(self, value: List['Artist']):
        validate_list(value, "favourite_artists", Artist)

        self._favourite_artists = value

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "subscribed": self._subscribed,
            "playlists": [p.serialize() for p in self._playlists],
            "favourite_tracks": [t.serialize() for t in self._favourite_tracks],
            "favourite_albums": [a.serialize() for a in self._favourite_albums],
            "favourite_artists": [a.serialize() for a in self._favourite_artists]
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'User':
        return cls(
            user_id=data.get("id"),
            name=data.get("name"),
            email=data.get("email"),
            subscribed=data.get("subscribed"),
            playlists=[Playlist.deserialize(playlist) for playlist in data.get("playlists")],
            favourite_tracks=[Track.deserialize(track) for track in data.get("favourite_tracks")],
            favourite_albums=[Album.deserialize(album) for album in data.get("favourite_albums")],
            favourite_artists=[Artist.deserialize(artist) for artist in data.get("favourite_artists")]
        )


class Artist(Person):
    """Класс, описывающий музыканта"""

    def __init__(self, artist_id: str, name: str, email: str,
                 tracks: Optional[List['Track']] = None, albums: Optional[List['Album']] = None,
                 collabed_tracks: Optional[List['Track']] = None, collabed_albums:Optional[List['Album']] = None,
                 produced_tracks: Optional[List['Track']] = None):
        super().__init__(artist_id, name, email)

        self._tracks = tracks or []
        self._albums = albums or []

        self._collabed_tracks = collabed_tracks or []
        self._collabed_albums = collabed_albums or []

        self._produced_tracks = produced_tracks or []

    @property
    def artist_id(self) -> str:
        return self.person_id

    @property
    def tracks(self) -> List['Track']:
        return self._tracks.copy()

    @tracks.setter
    def tracks(self, value: List['Track']):
        validate_list(value, "tracks", Track)

        self._tracks = value

    @property
    def albums(self) -> List['Album']:
        return self._albums.copy()

    @albums.setter
    def albums(self, value: List['Album']):
        validate_list(value, "albums", Album)

        self._albums = value

    @property
    def collabed_tracks(self) -> List['Track']:
        return self._collabed_tracks.copy()

    @collabed_tracks.setter
    def collabed_tracks(self, value: List['Track']):
        validate_list(value, "collabed_tracks", Track)

        self._collabed_tracks = value

    @property
    def collabed_albums(self) -> List['Album']:
        return self._collabed_albums.copy()

    @collabed_albums.setter
    def collabed_albums(self, value: List['Album']):
        validate_list(value, "collabed_albums", Album)

        self._collabed_albums = value

    @property
    def produced_tracks(self) -> List['Track']:
        return self._produced_tracks.copy()

    @produced_tracks.setter
    def produced_tracks(self, value: List['Track']):
        validate_list(value, "produced_tracks", Track)

        self._produced_tracks = value

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "tracks": [track.serialize() for track in self._tracks],
            "albums": [album.serialize() for album in self._albums],
            "collabed_tracks": [track.serialize() for track in self._collabed_tracks],
            "collabed_albums": [album.serialize() for album in self._collabed_albums],
            "produced_tracks": [track.serialize() for track in self._produced_tracks]
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Artist':
        tracks_data = data.get("tracks", [])
        albums_data = data.get("albums", [])

        collabed_tracks_data = data.get("collabed_tracks", [])
        collabed_albums_data = data.get("collabed_albums", [])

        produced_tracks_data = data.get("produced_tracks", [])

        return cls(
            artist_id=data.get("id"),
            name=data.get("name"),
            email=data.get("email"),
            tracks=[Track.deserialize(track) for track in tracks_data],
            albums=[Album.deserialize(album) for album in albums_data],
            collabed_tracks=[Track.deserialize(track) for track in collabed_tracks_data],
            collabed_albums=[Album.deserialize(album) for album in collabed_albums_data],
            produced_tracks=[Track.deserialize(track) for track  in produced_tracks_data]
        )


class Admin(Person):
    """Класс, описывающий администратора"""

    def __init__(self, admin_id: str, name: str, email: str, permissions: Optional[List[Permission]] = None):
        super().__init__(admin_id, name, email)

        self._permissions = permissions or []

    @property
    def admin_id(self) -> str:
        return self.person_id

    @property
    def permissions(self) -> List[Permission]:
        return self._permissions.copy()

    @permissions.setter
    def permissions(self, value: List[Permission]):
        validate_list(value, "permissions", Permission)

        self._permissions = value

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "permissions": [permission.value for permission in self._permissions]
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Admin':
        return cls(
            admin_id=data.get("id"),
            name=data.get("name"),
            email=data.get("email"),
            permissions=[Permission(permission) for permission in data.get("permissions", [])],
        )


class Collection(Serializable):
    """
    Класс, описывающий коллекцию

    В коллекции могут храниться другие объекты.
    """

    def __init__(self, collection_id: str, title: str, contents: List['Content'],
                 creator_id: str, collaborator_ids: Optional[List[str]] = None):
        self._collection_id = collection_id
        self._title = title
        self._contents = contents
        self._creator_id = creator_id

        self._collaborator_ids = collaborator_ids or []

    @property
    def collection_id(self) -> str:
        return self._collection_id

    @property
    def creator_id(self) -> str:
        return self._creator_id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        validate_str(value, "title")

        self._title = value

    @property
    def contents(self) -> List['Content']:
        return self._contents.copy()

    @contents.setter
    def contents(self, value: List['Content']):
        validate_list(value, "contents", Content)

        self._contents = value

    def add_content(self, content: 'Content'):
        self._contents.append(content)

        self.update()

    def remove_content(self, content: 'Content'):
        self._contents.remove(content)

        self.update()

    def pop_content(self, index: int = 0) -> Optional['Content']:
        try:
            content = self._contents.pop(index)

            self.update()

            return content
        except IndexError:
            print(CustomIndexError())

            return None

    @property
    def collaborator_ids(self) -> List[str]:
        return self._collaborator_ids.copy()

    def refresh_collaborator_ids(self):
        new_collaborator_ids = set()

        for content in self._contents:
            if hasattr(content, "collaborator_ids"):
                for collaborator_id in content.collaborator_ids:
                    new_collaborator_ids.add(collaborator_id)

        self._collaborator_ids = list(new_collaborator_ids)

    def update(self):
        self.refresh_collaborator_ids()

    # @collaborator_ids.setter
    # def collaborator_ids(self, value: List[str]):
    #     self._validate_list(value, "collaborator_ids", str)
    #
    #     self._collaborator_ids = value

    def serialize(self) -> Dict[str, Any]:
        return {
            "id": self._collection_id,
            "title": self._title,
            "contents": [c.serialize() for c in self._contents],
            "creator_id": self._creator_id,
            "collaborator_ids": self._collaborator_ids.copy(),
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Collection':
        return cls(
            collection_id=data.get("id"),
            title=data.get("title"),
            contents=[Content.deserialize(content) for content in data.get("contents", [])],
            creator_id=data.get("creator_id"),
            collaborator_ids=data.get("collaborator_ids", [])
        )


class Album(Collection):
    """
    Класс, описывающий альбомы

    Альбомы создаются музыкантами и содержат в себе треки.
    """

    def __init__(self, album_id: str, title: str, tracks: List['Track'],
                 artist_id: str, collaborator_ids: Optional[List[str]] = None,
                 genres: Optional[List[TrackGenre]] = None):
        super().__init__(album_id, title, tracks, artist_id, collaborator_ids)

        self._genres = genres or []
        if not self._genres:
            self.refresh_genres()

    @property
    def album_id(self) -> str:
        return self.collection_id

    @property
    def genres(self) -> List[TrackGenre]:
        return self._genres.copy()

    def refresh_genres(self):
        new_genres = set()

        for track in self.contents:
            if hasattr(track, "genres"):
                for genre in track.genres:
                    new_genres.add(genre)

        self._genres = list(new_genres)

    def update(self):
        self.refresh_collaborator_ids()

        self.refresh_genres()

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "genres": [genre.value for genre in self._genres]
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Album':
        return cls(
            album_id=data.get("id"),
            title=data.get("title"),
            tracks=[Track.deserialize(t) for t in data.get("contents", [])],
            artist_id=data.get("creator_id"),
            collaborator_ids=data.get("collaborator_ids", []),
            genres=[TrackGenre(genre) for genre in data.get("genres", [])]
        )


class Playlist(Collection):
    """
    Класс, описывающий плейлисты

    Плейлисты создаются пользователями и содержат в себе треки.
    """

    def __init__(self, playlist_id: str, title: str, tracks: List['Track'], owner_id: str,
                 genres: Optional[List[TrackGenre]] = None):
        super().__init__(playlist_id, title, tracks, owner_id)

        self._genres = genres or []
        if not self._genres:
            self.refresh_genres()

    @property
    def playlist_id(self) -> str:
        return self.collection_id

    @property
    def genres(self) -> List[TrackGenre]:
        return self._genres.copy()

    def refresh_genres(self):
        new_genres = set()

        for track in self.contents:
            if hasattr(track, "genres"):
                for genre in track.genres:
                    new_genres.add(genre)

        self._genres = list(new_genres)

    def update(self):
        self.refresh_collaborator_ids()

        self.refresh_genres()

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "genres": [genre.value for genre in self._genres]
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Playlist':
        return cls(
            playlist_id=data.get("id"),
            title=data.get("title"),
            tracks=[Track.deserialize(t) for t in data.get("contents", [])],
            owner_id=data.get("creator_id"),
            genres=[TrackGenre(genre) for genre in data.get("genres", [])]
        )


class AudioBook(Collection):
    """
    Класс, описывающий аудиокнигу

    Аудиокниги создаются музыкантами и содержат в себе главы.
    """

    def __init__(self, audiobook_id: str, title: str, chapters: List['AudioBookChapter'], author_id: str,
                 genres: Optional[List['AudioBookGenre']] = None):
        super().__init__(audiobook_id, title, chapters, author_id)

        self._genres = genres or []
        if not self._genres:
            self.refresh_genres()

    @property
    def audiobook_id(self) -> str:
        return self.collection_id

    @property
    def genres(self) -> List[AudioBookGenre]:
        return self._genres.copy()

    def refresh_genres(self):
        new_genres = set()

        for track in self.contents:
            if hasattr(track, "genres"):
                for genre in track.genres:
                    new_genres.add(genre)

        self._genres = list(new_genres)

    def update(self):
        self.refresh_collaborator_ids()

        self.refresh_genres()

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "genres": [genre.value for genre in self._genres]
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'AudioBook':
        return cls(
            audiobook_id=data.get("id"),
            title=data.get("title"),
            chapters=[AudioBookChapter.deserialize(a) for a in data.get("contents", [])],
            author_id=data.get("creator_id"),
            genres=[AudioBookGenre(genre) for genre in data.get("genres", [])]
        )


class Content(Serializable):
    """
    Класс, описывающий контент

    Контент может храниться в коллекциях.
    """

    def __init__(self, content_id: str, title: str, duration: timedelta, creator_id: str,
                 collaborator_ids: Optional[List[str]] = None, source_id: Optional[str] = None):
        self._content_id = content_id
        self._title = title

        self._duration = duration

        self._creator_id = creator_id

        self._collaborator_ids = collaborator_ids or []

        self._source_id = source_id

    @property
    def content_id(self) -> str:
        return self._content_id

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str):
        validate_str(value, "title")

        self._title = value

    @property
    def duration(self) -> timedelta:
        return self._duration

    @duration.setter
    def duration(self, value: timedelta):
        if not isinstance(value, timedelta):
            print("Значение длительности должно быть типа timedelta.")

            return

        if value.total_seconds() < 0:
            print("Длительность не может быть отрицательной.")

            return

        self._duration = value

    @property
    def artist_id(self) -> str:
        return self._creator_id

    @property
    def collaborator_ids(self) -> List[str]:
        return self._collaborator_ids.copy()

    @collaborator_ids.setter
    def collaborator_ids(self, value: List[str]):
        validate_list(value, "collaborator_ids", str)

        self._collaborator_ids = value

    @property
    def source_id(self) -> str:
        return self._source_id

    def add_collaborator_id(self, collaborator_id: str):
        if collaborator_id not in self._collaborator_ids:
            self._collaborator_ids.append(collaborator_id)

    def serialize(self) -> Dict[str, Any]:
        data = {
            "id": self._content_id,
            "title": self._title,
            "duration": int(self._duration.total_seconds()),
            "creator_id": self._creator_id,
            "collaborator_ids": self._collaborator_ids.copy(),
            "source_id": self._source_id
        }

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Content':
        return cls(
            content_id=data.get("id"),
            title=data.get("title"),
            duration=timedelta(seconds=data.get("duration", 0)),
            creator_id=data.get("creator_id"),
            collaborator_ids=data.get("collaborator_ids", []),
            source_id=data.get("source_id")
        )


class Track(Content):
    """Класс, описывающий трек"""

    def __init__(self, track_id: str, title: str, genres: List[TrackGenre], duration: timedelta, artist_id: str,
                 collaborator_ids: Optional[List[str]] = None, producer_ids: Optional[List[str]] = None,
                 album_id: Optional[str] = None):
        super().__init__(track_id, title, duration, artist_id, collaborator_ids, album_id)

        self._genres = genres
        self._producer_ids = producer_ids or []

    @property
    def track_id(self) -> str:
        return self.content_id

    @property
    def genres(self) -> List[TrackGenre]:
        return self._genres.copy()

    @genres.setter
    def genres(self, value: List[TrackGenre]):
        validate_list(value, "genres", TrackGenre)

        self._genres = value

    @property
    def producer_ids(self) -> List[str]:
        return self._producer_ids.copy()

    @producer_ids.setter
    def producer_ids(self, value: List[str]):
        validate_list(value, "producer_ids", str)

        self._producer_ids = value

    def add_genre(self, genre: TrackGenre):
        if genre not in self._genres:
            self._genres.append(genre)

    def add_producer_id(self, producer_id):
        if producer_id not in self._producer_ids:
            self._producer_ids.append(producer_id)

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "genres": [genre.value for genre in self._genres],
            "producer_ids": self._producer_ids.copy()
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Track':
        return cls(
            track_id=data.get("id"),
            title=data.get("title"),
            genres=[TrackGenre(genre) for genre in data.get("genres", [])],
            duration=timedelta(seconds=data.get("duration", 0)),
            artist_id=data.get("creator_id"),
            collaborator_ids=data.get("collaborator_ids", []),
            producer_ids=data.get("producer_ids", []),
            album_id=data.get("source_id")
        )


class AudioBookChapter(Content):
    """Класс, описывающий главу аудиокниги"""

    def __init__(self, chapter_id: str, title: str, duration: timedelta, author_id: str, audio_book_id: str,
                 collaborator_ids: Optional[List[str]] = None, narrator_ids: Optional[List[str]] = None):
        super().__init__(chapter_id, title, duration, author_id, collaborator_ids, audio_book_id)

        self._narrator_ids = narrator_ids or [author_id]

    @property
    def chapter_id(self) -> str:
        return self.content_id

    @property
    def narrator_ids(self) -> List[str]:
        return self._narrator_ids.copy()

    @narrator_ids.setter
    def narrator_ids(self, value: List[str]):
        validate_list(value, "narrator_ids", str)

        self._narrator_ids = value

    def add_narrator_id(self, narrator_id: str):
        if narrator_id not in self._narrator_ids:
            self._narrator_ids.append(narrator_id)

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "narrator_ids": self._narrator_ids.copy(),
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'AudioBookChapter':
        return cls(
            chapter_id=data.get("id"),
            title=data.get("title"),
            duration=timedelta(seconds=data.get("duration", 0)),
            author_id=data.get("creator_id"),
            collaborator_ids=data.get("collaborator_ids", []),
            narrator_ids=data.get("narrator_ids", []),
            audio_book_id=data.get("source_id")
        )


class RepeatModeValues(Enum):
    NONE = "none"
    ONE = "one"
    ALL = "all"


class MusicPlayer:
    """Класс, описывающий музыкальный плеер"""

    def __init__(self, music_player_id: str, user: 'User'):
        self._music_player_id = music_player_id
        self._user = user

        self._current_track: Optional['Track'] = None
        self._current_playlist: Optional['Playlist'] = None

        self._is_playing: bool = False
        self._volume: float = 0.8
        self._current_track_position: timedelta = timedelta(seconds=0)

        self._shuffle_mode: bool = False
        self._repeat_mode: RepeatModeValues = RepeatModeValues.NONE
        self._playback_speed: float = 1.0

        self._history: list['Track'] = []

        self._start_time: Optional[float] = None

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def current_track(self) -> Optional['Track']:
        return self._current_track

    @property
    def current_playlist(self) -> Optional['Playlist']:
        return self._current_playlist

    def status(self) -> str:
        if not self._current_track:
            return f"{MUSIC_PLAYER_PREFIX} Сейчас трек не выбран."

        state = "Играет" if self._is_playing else "Пауза"

        pos = int(self._current_track_position.total_seconds())
        dur = int(self._current_track.duration.total_seconds())
        vol = int(self._volume * 100)

        return f"{MUSIC_PLAYER_PREFIX} {state}: {self._current_track.title} [{pos}/{dur} сек.] Громкость: {vol}%"

    def load_playlist(self, playlist: 'Playlist'):
        self._current_playlist = playlist
        self._current_track = playlist.contents[0] if playlist.contents else None

        self._is_playing = False

        self._current_track_position = timedelta(seconds=0)

        self._history.clear()

        print(f"{MUSIC_PLAYER_PREFIX} Загружен плейлист '{playlist.title}'")

    def play(self, track: Optional['Track'] = None):
        if track:
            self._current_track = track

        if not self._current_track:
            print(f"{MUSIC_PLAYER_PREFIX} Нет трека для воспроизведения.")

            return

        self._is_playing = True

        self._start_time = time.time()

        print(f"{MUSIC_PLAYER_PREFIX} Играет: {self._current_track.title}")

    def pause(self):
        if not self._is_playing:
            print(f"{MUSIC_PLAYER_PREFIX} Уже на паузе.")

            return

        elapsed = (time.time() - self._start_time) * self._playback_speed

        self._current_track_position += timedelta(seconds=elapsed)

        self._is_playing = False

        pos = int(self._current_track_position.total_seconds())

        print(f"{MUSIC_PLAYER_PREFIX} Пауза на {pos} сек.")

    def stop(self):
        if not self._current_track:
            return

        self._is_playing = False

        self._current_track_position = timedelta(seconds=0)

        print(f"{MUSIC_PLAYER_PREFIX} Остановлено.")

    def next_track(self):
        if not self._current_playlist or not self._current_playlist.contents:
            print(f"{MUSIC_PLAYER_PREFIX} Плейлист пуст.")

            return

        playlist = self._current_playlist.contents

        if not self._current_track or self._current_track not in playlist:
            self._current_track = playlist[0]

            current_index = 0
        else:
            current_index = playlist.index(self._current_track)

        if self._shuffle_mode:
            next_track = random.choice(playlist)
        else:
            next_index = (current_index + 1) % len(playlist)
            next_track = playlist[next_index]

        if self._repeat_mode == RepeatModeValues.ONE:
            next_track = self._current_track

        if self._repeat_mode == RepeatModeValues.NONE and current_index == len(playlist) - 1:
            self.stop()

            print(f"{MUSIC_PLAYER_PREFIX} Плейлист закончился.")

            return

        self._history.append(self._current_track)

        self.play(next_track)

    def previous_track(self):
        if not self._history:
            print(f"{MUSIC_PLAYER_PREFIX} История пуста.")

            return

        prev_track = self._history.pop()
        self.play(prev_track)

    def set_volume(self, value: float):
        self._volume = max(0.0, min(1.0, value))

        vol = int(self._volume * 100)

        print(f"{MUSIC_PLAYER_PREFIX} Громкость: {vol}%")

    def toggle_shuffle_mod(self):
        self._shuffle_mode = not self._shuffle_mode

        mode = "включен" if self._shuffle_mode else "выключен"

        print(f"{MUSIC_PLAYER_PREFIX} Shuffle мод {mode}")

    def set_repeat_mode(self, mode: RepeatModeValues):
        self._repeat_mode = mode

        print(f"{MUSIC_PLAYER_PREFIX} Режим повтора: {mode}")

    def set_playback_speed(self, speed: float):
        if speed <= 0:
            print(f"{MUSIC_PLAYER_PREFIX} Ошибка: скорость должна быть > 0")

            return

        self._playback_speed = speed

        print(f"{MUSIC_PLAYER_PREFIX} Скорость воспроизведения: x{speed}")


if __name__ == "__main__":
    user = User(
        user_id="user_1",
        name="Slade",
        email="slade@gmail.com",
        subscribed=True
    )

    assert isinstance(user, Person)
    print("User наследует Person")

    artist = Artist(
        artist_id="artist_1",
        name="Rockman",
        email="rockman@gmail.com"
    )

    assert isinstance(artist, Person)
    print("Artist наследует Person")

    admin = Admin(
        admin_id="admin_1",
        name="Admin",
        email="admin@gmail.com",
        permissions=[Permission.VIEW_USERS, Permission.EDIT_USERS]
    )

    assert isinstance(admin, Person)
    print("Admin наследует Person")

    track = Track(
        track_id="track_1",
        title="Marusya",
        genres=[TrackGenre.ROCK],
        duration=timedelta(seconds=240),
        artist_id=artist.artist_id
    )

    assert isinstance(track, Content)
    print("Track наследует Content")

    chapter = AudioBookChapter(
        chapter_id="chapter_1",
        title="Глава 1",
        duration=timedelta(minutes=5),
        author_id="artist_2",
        audio_book_id="book_1"
    )

    assert isinstance(chapter, Content)
    print("AudioBookChapter наследует Content")

    album = Album(
        album_id="album_1",
        title="Power Music",
        tracks=[track],
        artist_id=artist.artist_id
    )

    assert isinstance(album, Collection)
    print("Album наследует Collection")

    playlist = Playlist(
        playlist_id="playlist_1",
        title="Музыка без АП",
        tracks=[track],
        owner_id=user.user_id
    )

    assert isinstance(playlist, Collection)
    print("Playlist наследует Collection")

    audiobook = AudioBook(
        audiobook_id="book_1",
        title="Релиз в продакшен без ошибок",
        chapters=[chapter],
        author_id="author_2"
    )

    assert isinstance(audiobook, Collection)
    print("AudioBook наследует Collection")

    player = MusicPlayer("music_player_1", user)
    player.load_playlist(playlist)
    player.play()
    player.pause()
    player.next_track()
    player.set_volume(0.5)
    player.set_repeat_mode(RepeatModeValues.ALL)
    player.set_playback_speed(1.25)

    print("MusicPlayer работает")

    objects = [user, artist, admin, track, album, playlist, audiobook]

    json_handler = JSONFileHandler()
    xml_handler = XMLFileHandler()

    # JSON
    json_file = "data.json"
    json_handler.save(objects, json_file)

    print(f"JSON успешно сохранён в файл {json_file}")

    loaded_json = json_handler.load(json_file)

    assert isinstance(loaded_json, list)
    print("JSON успешно загружен")

    # XML
    xml_file = "data.xml"
    xml_handler.save(objects, xml_file)

    print(f"XML успешно сохранён в файл {xml_file}")

    loaded_xml = xml_handler.load(xml_file)

    assert isinstance(loaded_xml, list)
    print("XML успешно загружен")

    _ = Person.deserialize(user.serialize())
    _ = User.deserialize(user.serialize())
    _ = Artist.deserialize(artist.serialize())
    _ = Admin.deserialize(admin.serialize())
    _ = Track.deserialize(track.serialize())
    _ = Album.deserialize(album.serialize())
    _ = Playlist.deserialize(playlist.serialize())
    _ = AudioBook.deserialize(audiobook.serialize())
    _ = AudioBookChapter.deserialize(chapter.serialize())

    print("✅ Все классы успешно сериализуются и десериализуются")

    print("Проверка работоспособности завершена!")
