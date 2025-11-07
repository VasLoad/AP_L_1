from abc import ABC, abstractmethod
import json
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import timedelta
from xml.etree import ElementTree
import xml.dom.minidom as minidom
import time
import random

from config import DEFAULT_FILE_INDENT, MUSIC_PLAYER_PREFIX
from errors import DataError, EmptyValueError, InvalidTypeError, CustomIndexError
from utils import validate_str, validate_list, deserialize_union


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
    TECH = "tech"


class Permission(Enum):
    """Перечисляемый класс, описывающий привилегии администратора"""

    VIEW_USERS = "view_users"
    EDIT_USERS = "edit_users"
    BAN_USERS = "ban_users"
    SEE_ANALYTICS = "see_analytics"
    INVITE_ADMINS = "invite_admins"


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
    """Обработчик файлов .JSON"""

    def save(self, data: List[Serializable], filename: str):
        with open(filename, "w", encoding="utf-8") as file:
            json.dump([item.serialize() for item in data], file, indent=DEFAULT_FILE_INDENT, ensure_ascii=False)


    @classmethod
    def load(cls, filename: str) -> List[Dict[str, Any]]:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

class XMLFileHandler(FileHandler):
    """Обработчик XML-файлов с поддержкой вложенных объектов и Union-типов"""

    def save(self, data: List[Serializable], filename: str):
        root = ElementTree.Element("data")

        for item in data:
            item_elem = ElementTree.SubElement(root, "item")

            self._serialize_value(item_elem, item.serialize())

        rough_string = ElementTree.tostring(root, encoding="utf-8")
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent=" " * DEFAULT_FILE_INDENT, encoding="utf-8").decode()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

    def _serialize_value(self, parent: ElementTree.Element, value: Any):
        if isinstance(value, dict):
            for k, v in value.items():
                child = ElementTree.SubElement(parent, k)

                self._serialize_value(child, v)
        elif isinstance(value, list):
            for item in value:
                child = ElementTree.SubElement(parent, "item")

                self._serialize_value(child, item)
        else:
            parent.text = json.dumps(value, ensure_ascii=False) if value is not None else ""

    @classmethod
    def load(cls, filename: str) -> List[Dict[str, Any]]:
        tree = ElementTree.parse(filename)
        root = tree.getroot()
        result = []

        for item_elem in root.findall("item"):
            result.append(cls._deserialize_element(item_elem))

        return result

    @classmethod
    def _deserialize_element(cls, elem: ElementTree.Element) -> Any:
        data = {}

        children = list(elem)

        if not children:
            text = (elem.text or "").strip()

            if not text:
                return None
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text

        if all(child.tag == "item" for child in children):
            return [cls._deserialize_element(child) for child in children]
        else:
            for child in children:
                key = child.tag
                value = cls._deserialize_element(child)
                data[key] = value

            return data


class Person(Serializable, ABC):
    """Абстрактный класс, описывающий человека в системе"""

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
            raise InvalidTypeError("person_id", str, type(value))
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
                 favourite_albums: Optional[List['Album']] = None, favourite_artists: Optional[List['Artist']] = None,
                 favourite_audiobooks: Optional[List['AudioBook']] = None):
        super().__init__(user_id, name, email)

        self._subscribed = subscribed

        self._playlists = playlists or []
        self._favourite_tracks = favourite_tracks or []
        self._favourite_albums = favourite_albums or []
        self._favourite_artists = favourite_artists or []

        self._favourite_audiobooks = favourite_audiobooks or []

    @property
    def user_id(self) -> str:
        return self.person_id

    @property
    def subscribed(self) -> bool:
        return self._subscribed

    @subscribed.setter
    def subscribed(self, value: bool):
        if not isinstance(value, bool):
            raise InvalidTypeError("subscribed", bool, type(value))
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

    @property
    def favourite_audiobooks(self) -> List['AudioBook']:
        return self._favourite_audiobooks.copy()

    @favourite_audiobooks.setter
    def favourite_audiobooks(self, value: List['AudioBook']):
        validate_list(value, "favourite_audiobooks", AudioBook)

        self._favourite_audiobooks = value

    def add_playlist(self, playlist: 'Playlist'):
        if not isinstance(playlist, Playlist):
            raise InvalidTypeError("playlist", Playlist, type(playlist))

        if playlist not in self._playlists:
            self._playlists.append(playlist)

    def remove_playlist(self, playlist: 'Playlist'):
        if not isinstance(playlist, Playlist):
            raise InvalidTypeError("playlist", Playlist, type(playlist))

        if playlist in self._playlists:
            self._playlists.remove(playlist)
        else:
            print(f"Плейлист {getattr(playlist, "title", "None")} не найден.")

    def pop_playlist(self, index: int = 0) -> Optional['Playlist']:
        if not self._playlists:
            print("Список плейлистов пуст.")

            return None
        try:
            return self._playlists.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def add_favourite_track(self, favourite_track: 'Track'):
        if not isinstance(favourite_track, Track):
            raise InvalidTypeError("favourite_track", Track, type(favourite_track))

        if favourite_track not in self._favourite_tracks:
            self._favourite_tracks.append(favourite_track)

    def remove_favourite_track(self, favourite_track: 'Track'):
        if not isinstance(favourite_track, Track):
            raise InvalidTypeError("favourite_track", Track, type(favourite_track))

        if favourite_track in self._favourite_tracks:
            self._favourite_tracks.remove(favourite_track)
        else:
            print(f"Трек {getattr(favourite_track, "title", "None")} не найден.")

    def pop_favourite_track(self, index: int = 0) -> Optional['Track']:
        if not self._favourite_tracks:
            print("Список любимых треков пуст.")

            return None
        try:
            return self._favourite_tracks.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def add_favourite_album(self, favourite_album: 'Album'):
        if not isinstance(favourite_album, Album):
            raise InvalidTypeError("favourite_album", Album, type(favourite_album))

        if favourite_album not in self._favourite_albums:
            self._favourite_albums.append(favourite_album)

    def remove_favourite_album(self, favourite_album: 'Album'):
        if not isinstance(favourite_album, Album):
            raise InvalidTypeError("favourite_album", Album, type(favourite_album))

        if favourite_album in self._favourite_albums:
            self._favourite_albums.remove(favourite_album)
        else:
            print(f"Альбом {getattr(favourite_album, "title", "None")} не найден.")

    def pop_favourite_album(self, index: int = 0) -> Optional['Album']:
        if not self._favourite_albums:
            print("Список любимых альбомов пуст.")

            return None
        try:
            return self._favourite_albums.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def add_favourite_artist(self, favourite_artist: 'Artist'):
        if not isinstance(favourite_artist, Artist):
            raise InvalidTypeError("favourite_artist", Artist, type(favourite_artist))

        if favourite_artist not in self._favourite_artists:
            self._favourite_artists.append(favourite_artist)

    def remove_favourite_artist(self, favourite_artist: 'Artist'):
        if not isinstance(favourite_artist, Artist):
            raise InvalidTypeError("favourite_artist", Artist, type(favourite_artist))

        if favourite_artist in self._favourite_artists:
            self._favourite_artists.remove(favourite_artist)
        else:
            print(f"Артист {getattr(favourite_artist, "title", "None")} не найден.")

    def pop_favourite_artist(self, index: int = 0) -> Optional['Artist']:
        if not self._favourite_artists:
            print("Список любимых артистов пуст.")

            return None
        try:
            return self._favourite_artists.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def add_favourite_audiobook(self, favourite_audiobook: 'AudioBook'):
        if not isinstance(favourite_audiobook, AudioBook):
            raise InvalidTypeError("favourite_audiobook", AudioBook, type(favourite_audiobook))

        if favourite_audiobook not in self._favourite_audiobooks:
            self._favourite_audiobooks.append(favourite_audiobook)

    def remove_favourite_audiobook(self, favourite_audiobook: 'AudioBook'):
        if not isinstance(favourite_audiobook, AudioBook):
            raise InvalidTypeError("favourite_audiobook", AudioBook, type(favourite_audiobook))

        if favourite_audiobook in self._favourite_audiobooks:
            self._favourite_audiobooks.remove(favourite_audiobook)
        else:
            print(f"Аудиокнига {getattr(favourite_audiobook, "title", "None")} не найдена.")

    def pop_favourite_audiobook(self, index: int = 0) -> Optional['AudioBook']:
        if not self._favourite_artists:
            print("Список любимых аудиокниг пуст.")

            return None
        try:
            return self._favourite_audiobooks.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "subscribed": self._subscribed,
            "playlists": [playlist.serialize() for playlist in self._playlists],
            "favourite_tracks": [track.serialize() for track in self._favourite_tracks],
            "favourite_albums": [album.serialize() for album in self._favourite_albums],
            "favourite_artists": [artist.serialize() for artist in self._favourite_artists],
            "favourite_audiobooks": [audiobook.serialize() for audiobook in self._favourite_audiobooks]
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'User':
        return cls(
            user_id=data.get("id"),
            name=data.get("name"),
            email=data.get("email"),
            subscribed=data.get("subscribed"),
            playlists=[Playlist.deserialize(playlist) for playlist in data.get("playlists", [])],
            favourite_tracks=[Track.deserialize(track) for track in data.get("favourite_tracks", [])],
            favourite_albums=[Album.deserialize(album) for album in data.get("favourite_albums", [])],
            favourite_artists=[Artist.deserialize(artist) for artist in data.get("favourite_artists", [])],
            favourite_audiobooks=[AudioBook.deserialize(audiobook) for audiobook in data.get("favourite_audiobooks", [])]
        )


class Artist(Person):
    """Класс, описывающий музыканта"""

    def __init__(self, artist_id: str, name: str, email: str,
                 tracks: Optional[List[Union['Track', 'AudioBookChapter']]] = None, albums: Optional[List[Union['Album', 'AudioBook']]] = None,
                 collabed_tracks: Optional[List[Union['Track', 'AudioBookChapter']]] = None, collabed_albums: Optional[List[Union['Album', 'AudioBook']]] = None,
                 produced_tracks: Optional[List[Union['Track', 'AudioBookChapter']]] = None):
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
    def tracks(self) -> List[Union['Track', 'AudioBookChapter']]:
        return self._tracks.copy()

    @tracks.setter
    def tracks(self, value: List[Union['Track', 'AudioBookChapter']]):
        validate_list(value, "tracks", Union[Track, AudioBookChapter])

        self._tracks = value

    @property
    def albums(self) -> List[Union['Album', 'AudioBook']]:
        return self._albums.copy()

    @albums.setter
    def albums(self, value: List[Union['Album', 'AudioBook']]):
        validate_list(value, "albums", Union[Album, AudioBook])

        self._albums = value

    @property
    def collabed_tracks(self) -> List[Union['Track', 'AudioBookChapter']]:
        return self._collabed_tracks.copy()

    @collabed_tracks.setter
    def collabed_tracks(self, value: List[Union['Track', 'AudioBookChapter']]):
        validate_list(value, "collabed_tracks", Union[Track, AudioBookChapter])

        self._collabed_tracks = value

    @property
    def collabed_albums(self) -> List[Union['Album', 'AudioBook']]:
        return self._collabed_albums.copy()

    @collabed_albums.setter
    def collabed_albums(self, value: List[Union['Album', 'AudioBook']]):
        validate_list(value, "collabed_albums", Union[Album, AudioBook])

        self._collabed_albums = value

    @property
    def produced_tracks(self) -> List[Union['Track', 'AudioBookChapter']]:
        return self._produced_tracks.copy()

    @produced_tracks.setter
    def produced_tracks(self, value: List[Union['Track', 'AudioBookChapter']]):
        validate_list(value, "produced_tracks", Union[Track, AudioBookChapter])

        self._produced_tracks = value

    def add_track(self, track: Union['Track','AudioBookChapter']):
        if not isinstance(track, (Track, AudioBookChapter)):
            raise InvalidTypeError("track", Union[Track, AudioBookChapter], type(track))

        if track not in self._tracks:
            self._tracks.append(track)

    def remove_track(self, track: Union['Track', 'AudioBookChapter']):
        if not isinstance(track, (Track, AudioBookChapter)):
            raise InvalidTypeError("track", Union[Track, AudioBookChapter], type(track))

        if track in self._tracks:
            self._tracks.remove(track)
        else:
            print(f"Трек {getattr(track, "title", "None")} не найден.")

    def pop_track(self, index: int = 0) -> Optional[Union['Track', 'AudioBookChapter']]:
        if not self._tracks:
            print("Список треков пуст.")

            return None
        try:
            return self._tracks.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def add_album(self, album: Union['Album', 'AudioBook']):
        if not isinstance(album, Union[Album, AudioBook]):
            raise InvalidTypeError("album", Union[Album, AudioBook], type(album))

        if album not in self._albums:
            self._albums.append(album)

    def remove_album(self, album: Union['Album', 'AudioBook']):
        if not isinstance(album, (Album, AudioBook)):
            raise InvalidTypeError("album", Union[Album, AudioBook], type(album))

        if album in self._albums:
            self._albums.remove(album)
        else:
            print(f"Альбом {getattr(album, "title", "None")} не найден.")

    def pop_album(self, index: int = 0) -> Optional[Union['Album', 'AudioBook']]:
        if not self._albums:
            print("Список альбомов пуст.")

            return None
        try:
            return self._albums.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def add_collabed_track(self, collabed_track: Union['Track','AudioBookChapter']):
        if not isinstance(collabed_track, (Track, AudioBookChapter)):
            raise InvalidTypeError("collabed_track", Union[Track, AudioBookChapter], type(track))

        if collabed_track not in self._collabed_tracks:
            self._collabed_tracks.append(collabed_track)

    def remove_collabed_track(self, collabed_track: Union['Track', 'AudioBookChapter']):
        if not isinstance(collabed_track, (Track, AudioBookChapter)):
            raise InvalidTypeError("collabed_track", Union[Track, AudioBookChapter], type(collabed_track))

        if collabed_track in self._collabed_tracks:
            self._collabed_tracks.remove(collabed_track)
        else:
            print(f"Совместный трек {getattr(collabed_track, "title", "None")} не найден.")

    def pop_collabed_track(self, index: int = 0) -> Optional[Union['Track', 'AudioBookChapter']]:
        if not self._collabed_tracks:
            print("Список совместных треков пуст.")

            return None
        try:
            return self._collabed_tracks.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def add_collabed_album(self, collabed_album: Union['Album', 'AudioBook']):
        if not isinstance(collabed_album, (Album, AudioBook)):
            raise InvalidTypeError("collabed_album", Union[Album, AudioBook], type(collabed_album))

        if collabed_album not in self._collabed_albums:
            self._collabed_albums.append(collabed_album)

    def remove_collabed_album(self, collabed_album: Union['Album', 'AudioBook']):
        if not isinstance(collabed_album, (Album, AudioBook)):
            raise InvalidTypeError("collabed_album", Union[Album, AudioBook], type(collabed_album))

        if collabed_album in self._collabed_albums:
            self._collabed_albums.remove(collabed_album)
        else:
            print(f"Совместный альбом {getattr(collabed_album, "title", "None")} не найден.")

    def pop_collabed_album(self, index: int = 0) -> Optional[Union['Album', 'AudioBook']]:
        if not self._collabed_albums:
            print("Список совместных альбомов пуст.")

            return None
        try:
            return self._collabed_albums.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def add_produced_track(self, produced_track: Union['Track', 'AudioBookChapter']):
        if not isinstance(produced_track, (Track, AudioBookChapter)):
            raise InvalidTypeError("produced_track", Union[Track, AudioBookChapter], type(produced_track))

        if produced_track not in self._produced_tracks:
            self._produced_tracks.append(produced_track)

    def remove_produced_track(self, produced_track: Union['Track', 'AudioBookChapter']):
        if not isinstance(produced_track, (Track, AudioBookChapter)):
            raise InvalidTypeError("produced_track", Union[Track, AudioBookChapter], type(produced_track))

        if produced_track in self._produced_tracks:
            self._produced_tracks.remove(produced_track)
        else:
            print(f"Спродюсированный трек {getattr(produced_track, "title", "None")} не найден.")

    def pop_produced_track(self, index: int = 0) -> Optional[Union['Track', 'AudioBookChapter']]:
        if not self._produced_tracks:
            print("Список спродюсированных треков пуст.")

            return None
        try:
            return self._produced_tracks.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "tracks": [
                {
                    "type": type(track).__name__,
                    "data": track.serialize()
                } for track in self._tracks],
            "albums": [
                {
                    "type": type(album).__name__,
                    "data": album.serialize()
                } for album in self._albums],
            "collabed_tracks": [
                {
                    "type": type(collabed_track).__name__,
                    "data": collabed_track.serialize()
                } for collabed_track in self._collabed_tracks],
            "collabed_albums": [
                {
                    "type": type(collabed_album).__name__,
                    "data": collabed_album.serialize()
                } for collabed_album in self._collabed_albums],
            "produced_tracks": [
                {
                    "type": type(produced_track).__name__,
                    "data": produced_track.serialize()
                } for produced_track in self._produced_tracks],
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Artist':

        tracks = deserialize_union(data.get("tracks", []), [Track, AudioBookChapter])
        albums = deserialize_union(data.get("albums", []), [Album, AudioBook])

        collabed_tracks = deserialize_union(data.get("collabed_tracks", []), [Track, AudioBookChapter])
        collabed_albums = deserialize_union(data.get("collabed_albums", []), [Album, AudioBook])

        produced_tracks = deserialize_union(data.get("produced_tracks", []), [Track, AudioBookChapter])

        return cls(
            artist_id=data.get("id"),
            name=data.get("name"),
            email=data.get("email"),
            tracks=tracks,
            albums=albums,
            collabed_tracks=collabed_tracks,
            collabed_albums=collabed_albums,
            produced_tracks=produced_tracks
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

    def add_permission(self, permission: Permission):
        if not isinstance(permission, Permission):
            raise InvalidTypeError("permission", Permission, type(permission))

        if permission not in self._permissions:
            self._permissions.append(permission)

    def remove_permission(self, permission: Permission):
        if not isinstance(permission, Permission):
            raise InvalidTypeError("permission", Permission, type(permission))

        if permission in self._permissions:
            self._permissions.remove(permission)
        else:
            print(f"Привилегия {permission.value} не найдена.")

    def pop_permission(self, index: int = 0) -> Optional[Permission]:
        if not self._permissions:
            print("Список привилегий пуст.")

            return None
        try:
            return self._permissions.pop(index)
        except IndexError:
            print(CustomIndexError())

            return None

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


class Collection(Serializable, ABC):
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


class MusicPlayer(Serializable):
    """Класс, описывающий музыкальный плеер"""

    def __init__(self, music_player_id: str, user: 'User', current_track: Optional['Track'] = None,
                 current_playlist: Optional['Playlist'] = None, is_playing: Optional[bool] = False,
                 volume: Optional[float] = 0.8, current_track_position: Optional[timedelta] = timedelta(seconds=0),
                 shuffle_mode: Optional[bool] = False, repeat_mode: Optional[RepeatModeValues] = RepeatModeValues.NONE,
                 playback_speed: Optional[float] = 1, history: Optional[List[Union['Track', 'AudioBookChapter']]] = None,
                 start_time: Optional[float] = None):
        self._music_player_id = music_player_id
        self._user = user

        self._current_track = current_track
        self._current_playlist = current_playlist

        self._is_playing = is_playing
        self._volume = volume
        self._current_track_position = current_track_position

        self._shuffle_mode = shuffle_mode
        self._repeat_mode = repeat_mode
        self._playback_speed = playback_speed

        self._history = history or []

        self._start_time = start_time

    @property
    def music_player_id(self) -> str:
        return self._music_player_id

    @property
    def user(self) -> 'User':
        return self._user

    @property
    def current_track(self) -> Optional[Union['Track', 'AudioBookChapter']]:
        return self._current_track

    @property
    def current_playlist(self) -> Optional[Union['Playlist', 'AudioBook']]:
        return self._current_playlist

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def volume(self) -> float:
        return self._volume

    @property
    def current_track_position(self) -> timedelta:
        return self._current_track_position

    @property
    def shuffle_mode(self) -> bool:
        return self._shuffle_mode

    @property
    def repeat_mode(self) -> RepeatModeValues:
        return self._repeat_mode

    @property
    def playback_speed(self) -> float:
        return self._playback_speed

    @property
    def history(self) -> List[Union['Track', 'AudioBookChapter']]:
        return self._history

    @property
    def start_time(self) -> float:
        return self._start_time

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

    def serialize(self) -> Dict[str, Any]:
        return {
            "music_player_id": self._music_player_id,
            "user": self._user.serialize(),
            "current_track": self._current_track.serialize(),
            "current_playlist": self._current_playlist.serialize(),
            "is_playing": self.is_playing,
            "volume": self._volume,
            "current_track_position": self._current_track_position.total_seconds(),
            "shuffle_mode": self._shuffle_mode,
            "repeat_mode": self._repeat_mode.value,
            "playback_speed": self._playback_speed,
            "history": [
                {
                    "type": type(track).__name__,
                    "data": track.serialize()
                } for track in self._history],
            "start_time": self._start_time
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'MusicPlayer':
        history = deserialize_union(data.get("history", []), [Track, AudioBookChapter])

        return cls(
            music_player_id=data.get("music_player_id"),
            user=User.deserialize(data.get("user")),
            current_track=Track.deserialize(data.get("current_track")),
            current_playlist=Playlist.deserialize(data.get("current_playlist")),
            is_playing=data.get("is_playing"),
            volume=data.get("volume"),
            current_track_position=timedelta(seconds=data.get("current_track_position", 0)),
            shuffle_mode=data.get("shuffle_mode"),
            repeat_mode=RepeatModeValues(data.get("repeat_mode")),
            playback_speed=data.get("playback_speed"),
            history=history,
            start_time=data.get("start_time")
        )


if __name__ == "__main__":
    print("Запуск полной проверки сериализации/десериализации MusicPlayer...")
    print("=" * 80)

    print("1. Создание объектов с полным заполнением всех полей...")

    user = User(
        user_id="usr_001",
        name="Александра Ветрова",
        email="alex.vetrova@example.com",
        subscribed=True
    )

    artist = Artist(
        artist_id="art_001",
        name="Neon Pulse",
        email="contact@neonpulse.band"
    )

    admin = Admin(
        admin_id="adm_001",
        name="Root Admin",
        email="root@musicapp.lv",
        permissions=[
            Permission.VIEW_USERS,
            Permission.EDIT_USERS,
            Permission.BAN_USERS,
            Permission.SEE_ANALYTICS,
            Permission.INVITE_ADMINS
        ]
    )

    track = Track(
        track_id="trk_001",
        title="Midnight Echo",
        genres=[TrackGenre.ELECTRONIC, TrackGenre.POP],
        duration=timedelta(minutes=3, seconds=42),
        artist_id=artist.artist_id,
        collaborator_ids=["art_002"],
        producer_ids=["prod_001", "prod_002"],
        album_id="alb_001"
    )

    chapter = AudioBookChapter(
        chapter_id="chp_001",
        title="Глава 1: Первые шаги в коде",
        duration=timedelta(minutes=18, seconds=15),
        author_id=artist.artist_id,
        audio_book_id="abk_001",
        collaborator_ids=["voice_001"],
        narrator_ids=["voice_001", "voice_002"]
    )

    album = Album(
        album_id="alb_001",
        title="Synthetic Dreams",
        tracks=[track],
        artist_id=artist.artist_id,
        collaborator_ids=["art_002"],
        genres=[TrackGenre.ELECTRONIC, TrackGenre.POP]
    )

    playlist = Playlist(
        playlist_id="pl_001",
        title="Ночь в неоновом городе",
        tracks=[track],
        owner_id=user.user_id,
        genres=[TrackGenre.ELECTRONIC]
    )

    audiobook = AudioBook(
        audiobook_id="abk_001",
        title="Python: От новичка до мастера",
        chapters=[chapter],
        author_id=artist.artist_id,
        genres=[AudioBookGenre.TECH, AudioBookGenre.COMEDY]
    )

    print("2. Установка связей между объектами...")

    user.add_playlist(playlist)
    user.add_favourite_track(track)
    user.add_favourite_album(album)
    user.add_favourite_artist(artist)
    user.add_favourite_audiobook(audiobook)

    artist.add_track(track)
    artist.add_album(album)
    artist.add_collabed_track(chapter)
    artist.add_collabed_album(audiobook)
    artist.add_produced_track(track)

    print("3. Создание MusicPlayer с полной нагрузкой...")

    player = MusicPlayer(
        music_player_id="mp_001",
        user=user,
        current_track=track,
        current_playlist=playlist,
        is_playing=True,
        volume=0.72,
        current_track_position=timedelta(minutes=1, seconds=23),
        shuffle_mode=True,
        repeat_mode=RepeatModeValues.ALL,
        playback_speed=1.25,
        history=[track, chapter],
        start_time=time.time() - 83
    )

    # Симуляция работы
    # player.load_playlist(playlist)
    # player.play(track)

    print("4. Сохранение MusicPlayer...")

    filename_base = "data"
    json_handler = JSONFileHandler()
    xml_handler = XMLFileHandler()

    # JSON
    json_file = f"{filename_base}.json"
    json_handler.save([player], json_file)  # Только один объект!
    print(f"   JSON сохранён: {json_file}")

    # XML
    xml_file = f"{filename_base}.xml"
    xml_handler.save([player], xml_file)
    print(f"   XML сохранён: {xml_file}")

    print("5. Загрузка и полная проверка восстановленного MusicPlayer...")

    print("   Проверка JSON...")
    loaded_json = json_handler.load(json_file)
    assert len(loaded_json) == 1, "JSON должен содержать ровно 1 объект"
    deserialized_json = MusicPlayer.deserialize(loaded_json[0])

    print("   Проверка XML...")
    loaded_xml = xml_handler.load(xml_file)
    assert len(loaded_xml) == 1, "XML должен содержать ровно 1 объект"
    deserialized_xml = MusicPlayer.deserialize(loaded_xml[0])

    print("6. Глубокая проверка всех полей MusicPlayer...")


    def check_player(p, name):
        print(f"   Проверка {name}:")

        assert p.music_player_id == "mp_001", "Неверный ID плеера"
        assert p.is_playing is True, "Должно играть"
        assert abs(p.volume - 0.72) < 1e-6, "Неверная громкость"
        assert p.current_track_position == timedelta(minutes=1, seconds=23), "Неверная позиция"
        assert p.shuffle_mode is True, "Shuffle должен быть включён"
        assert p.repeat_mode == RepeatModeValues.ALL, "Неверный режим повтора"
        assert abs(p.playback_speed - 1.25) < 1e-6, "Неверная скорость"
        assert p.start_time is not None, "start_time должен быть"

        assert p.current_track is not None, "current_track не должен быть None"
        assert p.current_track.title == "Midnight Echo", "Неверный текущий трек"
        assert TrackGenre.ELECTRONIC in p.current_track.genres, "Неверный жанр трека"

        assert p.current_playlist is not None, "current_playlist не должен быть None"
        assert p.current_playlist.title == "Ночь в неоновом городе", "Неверный плейлист"
        assert len(p.current_playlist.contents) == 1, "Плейлист должен содержать 1 трек"

        assert len(p.history) == 2, "История должна содержать 2 элемента"
        assert isinstance(p.history[0], Track), "Первый в истории — должен быть Track"
        assert isinstance(p.history[1], AudioBookChapter), "Второй — AudioBookChapter"
        assert p.history[0].title == "Midnight Echo", "Неверный трек в истории"

        assert p.user.user_id == "usr_001", "Неверный пользователь"
        assert p.user.subscribed is True, "Пользователь должен быть подписан"
        assert len(p.user.playlists) == 1, "У пользователя должен быть 1 плейлист"
        assert len(p.user.favourite_tracks) == 1, "1 любимый трек"
        assert len(p.user.favourite_albums) == 1, "1 любимый альбом"
        assert len(p.user.favourite_artists) == 1, "1 любимый артист"
        assert len(p.user.favourite_audiobooks) == 1, "1 любимая аудиокнига"

        print(f"   {name}: ВСЁ ОК")


    check_player(deserialized_json, "JSON")
    check_player(deserialized_xml, "XML")

    print("7. Проверка метода status()...")
    status = player.status()
    assert "Играет" in status, "Статус должен показывать 'Играет'"
    assert "Midnight Echo" in status, "Название трека в статусе"
    assert "Громкость: 72%" in status, "Громкость в статусе"
    print("   status(): Работает корректно")

    print("=" * 80)
    print("ПРОВЕРКА ПРОЙДЕНА УСПЕШНО!")
    print(f"Созданные файлы:")
    print(f"   {json_file}")
    print(f"   {xml_file}")
    print("=" * 80)
