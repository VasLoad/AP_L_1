from abc import ABC, abstractmethod
import json
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import timedelta
from xml.etree import ElementTree
import xml.dom.minidom as minidom

from config import DEFAULT_INDENT
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
    """Перечисляемый класс, описывающий привелегии администратора"""

    VIEW_USERS = "view_users"
    EDIT_USERS = "edit_users"
    BAN_USERS = "ban_users"
    USE_PLAYGROUND = "see_analytics"
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


class FileFormats(Enum):
    """Перечисляемый класс, описывающий поддерживаемые файловые форматы"""

    JSON = "json"
    XML = "xml"


class JSONFileHandler(FileHandler):
    """Класс, описывающий обработчик файлов .JSON"""

    def save(self, data: List[Serializable], filename: str):
        with open(filename, "w", encoding="utf-8") as file:
            json.dump([item.serialize() for item in data], file, indent=DEFAULT_INDENT, ensure_ascii=False)


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
        decorated_tree = minidom.parseString(tree).toprettyxml(indent=" " * DEFAULT_INDENT)

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


class FileHandlerSelector:
    """Класс, описывающий помощника выбора обработчика файлов"""

    @staticmethod
    def get_handler(file_format: FileFormats) -> FileHandler:
        handlers = {
            FileFormats.JSON: JSONFileHandler(),
            FileFormats.XML: XMLFileHandler()
        }

        if file_format not in handlers:
            raise ValueError(f"Формат не поддерживается: {file_format}")

        return handlers[file_format]


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

        self.collabed_albums = value

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
            "collabed_albums": [album for album in self._collabed_albums],
            "produced_tracks": [track for track in self._produced_tracks]
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
        permissions_data = data.get("permissions", [])

        return cls(
            admin_id=data.get("id"),
            name=data.get("name"),
            email=data.get("email"),
            permissions=[Permission(p) for p in permissions_data],
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
        return self._collection_id


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
            contents=data.get("contents", []),
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
        genres = set()

        for track in self.contents:
            if hasattr(track, "genre"):
                genres.add(track)

        self._genres = list(genres)


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
        genres = set()

        for track in self.contents:
            if hasattr(track, "genre"):
                genres.add(track)

        self._genres = list(genres)


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
        genres = set()

        for chapter in self.contents:
            if hasattr(chapter, "genre"):
                genres.add(chapter)

        self._genres = list(genres)


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

    def __init__(self, content_id: str, title: str, duration: timedelta, artist_id: str,
                 collaborator_ids: Optional[List[str]] = None, source_id: Optional[str] = None):
        self._content_id = content_id
        self._title = title

        self._duration = duration

        self._artist_id = artist_id

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
        return self._artist_id


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
            self.collaborator_ids.append(collaborator_id)


    def serialize(self) -> Dict[str, Any]:
        data = {
            "id": self._content_id,
            "title": self._title,
            "duration": int(self._duration.total_seconds()),
            "artist": self._artist_id,
            "collaborator_ids": self._collaborator_ids.copy(),
            "source": self._source_id
        }

        return data


    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Content':
        return cls(
            content_id=data.get("id"),
            title=data.get("title"),
            duration=timedelta(seconds=data.get("duration")),
            artist_id=data.get("artist_id"),
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
            duration=data.get("duration"),
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
            duration=data.get("duration"),
            author_id=data.get("artist_id"),
            collaborator_ids=data.get("collaborator_ids", []),
            narrator_ids=data.get("narrator_ids", []),
            audio_book_id=data.get("source_id")
        )


class MusicPlayer:
    """Класс, описывающий музыкальный плеер"""

    def __init__(self, music_player_id: str, user: User):
        self._music_player_id = music_player_id
        self._user = user

        self._current_track: Optional[Track] = None
        self._current_playlist: Optional[Playlist] = None

        self._is_playing: bool = False

        self._volume: float = 0.8
        self._current_track_position: float = 0.0

        self._shuffle_mode: bool = False
        self._repeat_mode: str = "none"
        self._playback_speed: float = 1.0
        self._equalizer_settings: dict[str, float] = {}

        self._history: list[Track] = []

    @property
    def get_id(self) -> str:
        return self._music_player_id


def full_serialization_test():
    artist = Artist(
        artist_id="artist_001",
        name="The Rockers",
        email="rockers@mail.com"
    )

    album = Album(
        album_id="album_001",
        title="Loud & Proud",
        tracks=[],  # заполним позже
        artist_id=artist.artist_id
    )

    track1 = Track(
        track_id="track_001",
        title="Thunder Road",
        genres=[TrackGenre.ROCK],
        duration=timedelta(minutes=1, seconds=15),
        artist_id=artist.artist_id
    )
    track2 = Track(
        track_id="track_002",
        title="Silent Nights",
        genres=[TrackGenre.CLASSIC],
        duration=timedelta(minutes=9, seconds=18),
        artist_id=artist.artist_id,
        album_id=album.album_id
    )

    tracks = [track1, track2]

    album.contents = tracks
    artist.tracks = tracks
    artist.album = album

    # Аудиокнига и главы
    chapter1 = AudioBookChapter(
        chapter_id="ch_001",
        title="The Beginning",
        duration=timedelta(minutes=3, seconds=42),
        author_id=artist.artist_id,
        audio_book_id="book_001"
    )
    chapter2 = AudioBookChapter(
        chapter_id="ch_002",
        title="The Fear",
        duration=timedelta(minutes=5, seconds=45),
        author_id=artist.artist_id,
        audio_book_id="book_001"
    )

    audio_book = AudioBook(
        audiobook_id="book_001",
        title="Story of Sound",
        chapters=[chapter1, chapter2],
        author_id=artist.artist_id,
        genres=[AudioBookGenre.HORROR]
    )

    # Пользователь, который любит этого артиста
    user = User(
        user_id="user_001",
        name="Alice",
        email="alice@mail.com",
        subscribed=True,
        playlists=[],
        favourite_tracks=[track1, track2],
        favourite_albums=[album],
        favourite_artists=[artist]
    )

    # Плейлист пользователя
    playlist = Playlist(
        playlist_id="playlist_001",
        title="My Favs",
        tracks=[track1, track2],
        owner_id=user.user_id
    )

    user._playlists = [playlist]

    # Админ с разрешениями
    admin = Admin(
        admin_id="admin_001",
        name="SuperAdmin",
        email="admin@mail.com",
        permissions=[Permission.VIEW_USERS, Permission.BAN_USERS]
    )

    # === 2. Сериализация в JSON ===
    json_handler = JSONFileHandler()

    objects_to_save = [user, artist, album, track1, track2, playlist, audio_book, chapter1, chapter2, admin]

    json_filename = "test_data.json"
    json_handler.save(objects_to_save, json_filename)

    print(f"✅ JSON сохранён: {json_filename}")

    # Проверим, что файл корректный
    with open(json_filename, "r", encoding="utf-8") as file:
        json_data = json.load(file)
    print(f"Пример JSON:\n{json.dumps(json_data[:2], indent=DEFAULT_INDENT, ensure_ascii=False)}\n")

    # === 3. Сериализация в XML ===
    xml_handler = XMLFileHandler()

    xml_filename = "test_data.xml"
    xml_handler.save(objects_to_save, xml_filename)

    print(f"✅ XML сохранён: {xml_filename}")

    # Проверим корректность XML
    xml_tree = ElementTree.parse(xml_filename)
    xml_root = xml_tree.getroot()
    print(f"Пример XML-первого элемента:\n{ElementTree.tostring(xml_root[0], encoding='unicode')}\n")

    # === 4. Проверка обратной загрузки ===
    json_loaded_data = json_handler.load(json_filename)
    xml_loaded_data = xml_handler.load(xml_filename)

    print("✅ JSON-загружено объектов:", len(json_loaded_data))
    print("✅ XML-загружено объектов:", len(xml_loaded_data))

    # === 5. Сравнение структуры JSON/XML данных ===
    def normalize(obj):
        """Удаляет различия в типах данных"""
        if isinstance(obj, dict):
            return {k: normalize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [normalize(v) for v in obj]
        return str(obj)

    json_norm = normalize(json_loaded_data)
    xml_norm = normalize(xml_loaded_data)

    print("🔍 Сравнение JSON и XML:")
    print("Совпадают по количеству элементов:", len(json_norm) == len(xml_norm))

    # Пример сверки первых записей
    print("\nСравнение первой записи:")
    print("JSON:", json_norm[0])
    print("XML :", xml_norm[0])

    result_user = User.deserialize(json_loaded_data[0])

    print(result_user.person_id)


if __name__ == "__main__":
    full_serialization_test()