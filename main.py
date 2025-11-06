from abc import ABC, abstractmethod
import json
from enum import Enum
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree
import xml.dom.minidom as minidom

DEFAULT_INDENT = 3

class TrackGenre(Enum):
    ROCK = "rock"
    POP = "pop"
    HIP_HOP = "hip-hop"
    ELECTRONIC = "electronic"
    CLASSIC = "classic"


class AudioBookChapterGenre(Enum):
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
        with open(filename, "w", encoding="utf-8") as file:
            json.dump([item.serialize() for item in data], file, indent=DEFAULT_INDENT, ensure_ascii=False)

    def load(self, filename: str) -> List[Dict[str, Any]]:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)


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
    @staticmethod
    def get_handler(format: FileFormats) -> FileHandler:
        handlers = {
            FileFormats.JSON: JSONFileHandler(),
            FileFormats.XML: XMLFileHandler()
        }

        if format not in handlers:
            raise ValueError(f"Формат не поддерживается: {format}")
        return handlers[format]


class Person(Serializable):
    def __init__(self, person_id: str, name: str, email: str):
        self._person_id = person_id
        self._name = name
        self._email = email

    @property
    def get_id(self) -> str:
        return self._person_id

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
    def get_id(self) -> str:
        return super().get_id

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
            playlists=[
                Playlist.deserialize(p) if isinstance(p, dict) else p
                for p in data.get("playlists", [])
            ],
            favourite_tracks=[
                Track.deserialize(t) if isinstance(t, dict) else t
                for t in data.get("favourite_tracks", [])
            ],
            favourite_albums=[
                Album.deserialize(a) if isinstance(a, dict) else a
                for a in data.get("favourite_albums", [])
            ],
            favourite_artists=[
                Artist.deserialize(a) if isinstance(a, dict) else a
                for a in data.get("favourite_artists", [])
            ]
        )


class Artist(Person):
    def __init__(self, artist_id: str, name: str, email: str,
                 tracks: Optional[List['Track']] = None, albums: Optional[List['Album']] = None):
        super().__init__(artist_id, name, email)

        self.tracks = tracks or []
        self.albums = albums or []

    @property
    def get_id(self) -> str:
        return super().get_id

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "tracks": [track.serialize() for track in self.tracks],
            "albums": [album.serialize() for album in self.albums]
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Artist':
        tracks_data = data.get("tracks", [])
        albums_data = data.get("albums", [])

        artist = cls(
            artist_id=data.get("id"),
            name=data.get("name"),
            email=data.get("email"),
            tracks=[Track.deserialize(t) for t in tracks_data],
            albums=[Album.deserialize(a) for a in albums_data]
        )

        return artist


class Admin(Person):
    def __init__(self, admin_id: str, name: str, email: str, permissions: Optional[List[Permission]] = None):
        super().__init__(admin_id, name, email)

        self.permissions = permissions or []

    @property
    def get_id(self) -> str:
        return super().get_id

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "permissions": [permission.value for permission in self.permissions]
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Admin':
        permissions_data = data.get("permissions", [])

        admin = cls(
            admin_id=data.get("id"),
            name=data.get("name"),
            email=data.get("email"),
            permissions=[Permission(p) for p in permissions_data],
        )

        return admin


class Collection(Serializable):
    def __init__(self, collection_id: str, title: str, contents: List['Content'],
                 creator_id: str, collaborator_ids: Optional[List[str]] = None):
        self.collection_id = collection_id
        self.title = title
        self.contents = contents
        self.creator_id = creator_id

        self.collaborator_ids = collaborator_ids or []

    @property
    def get_id(self) -> str:
        return self.collection_id

    def serialize(self) -> Dict[str, Any]:
        return {
            "id": self.collection_id,
            "title": self.title,
            "contents": [c.serialize() for c in self.contents],
            "creator_id": self.creator_id,
            "collaborator_ids": self.collaborator_ids.copy(),
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
    def __init__(self, album_id: str, title: str, tracks: List['Track'],
                 artist_id: str, collaborator_ids: Optional[List[str]] = None):
        super().__init__(album_id, title, tracks, artist_id, collaborator_ids)

    @property
    def get_id(self) -> str:
        return super().get_id

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Album':
        return cls(
            album_id=data.get("id"),
            title=data.get("title"),
            tracks=[Track.deserialize(t) for t in data.get("contents", [])],
            artist_id=data.get("creator_id"),
            collaborator_ids=data.get("collaborator_ids", [])
        )


class Playlist(Collection):
    def __init__(self, playlist_id: str, title: str, tracks: List['Track'], owner_id: str):
        super().__init__(playlist_id, title, tracks, owner_id)

    @property
    def get_id(self) -> str:
        return super().get_id

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Playlist':
        playlist = cls(
            playlist_id=data.get("id"),
            title=data.get("title"),
            tracks=[Track.deserialize(t) for t in data.get("contents", [])],
            owner_id=data.get("creator_id")
        )

        return playlist


class AudioBook(Collection):
    def __init__(self, collection_id: str, title: str, chapters: List['AudioBookChapter'], author_id: str):
        super().__init__(collection_id, title, chapters, author_id)

    @property
    def get_id(self) -> str:
        return super().get_id

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'AudioBook':
        audio_book = cls(
            collection_id=data.get("id"),
            title=data.get("title"),
            chapters=[AudioBookChapter.deserialize(a) for a in data.get("contents", [])],
            author_id=data.get("creator_id")
        )

        return audio_book


class Content(Serializable):
    def __init__(self, content_id: str, title: str, duration: float, artist_id: str,
                 collaborator_ids: Optional[List[str]] = None, source_id: Optional[str] = None):
        self.content_id = content_id
        self.title = title

        self.duration = duration

        self.artist_id = artist_id

        self.collaborator_ids = collaborator_ids or []

        self.source_id = source_id

    @property
    def get_id(self) -> str:
        return self.content_id

    def serialize(self) -> Dict[str, Any]:
        data = {
            "id": self.content_id,
            "title": self.title,
            "duration": self.duration,
            "artist": self.artist_id,
            "collaborator_ids": self.collaborator_ids.copy(),
            "source": self.source_id
        }

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Content':
        content = cls(
            content_id=data.get("id"),
            title=data.get("title"),
            duration=data.get("duration"),
            artist_id=data.get("artist_id"),
            collaborator_ids=data.get("collaborator_ids", []),
            source_id=data.get("source_id")
        )

        return content


class Track(Content):
    def __init__(self, track_id: str, title: str, genres: List[TrackGenre], duration: float, artist_id: str,
                 collaborator_ids: Optional[List[str]] = None, producer_ids: Optional[List[str]] = None,
                 album_id: Optional[str] = None):
        super().__init__(track_id, title, duration, artist_id, collaborator_ids, album_id)

        self.genres = genres
        self.producer_ids = producer_ids or []

    @property
    def get_id(self) -> str:
        return super().get_id

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "producer_ids": self.producer_ids.copy(),
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Track':
        track = cls(
            track_id=data.get("id"),
            title=data.get("title"),
            genres=[TrackGenre(genre) for genre in data.get("genres", [])],
            duration=data.get("duration"),
            artist_id=data.get("creator_id"),
            collaborator_ids=data.get("collaborator_ids", []),
            producer_ids=data.get("producer_ids", []),
            album_id=data.get("source_id")
        )

        return track


class AudioBookChapter(Content):
    def __init__(self, chapter_id: str, title: str, genres: List[AudioBookChapterGenre], duration: float, author_id: str,
                 collaborator_ids: Optional[List[str]] = None, audio_book_id: Optional[str] = None,
                 narrator_ids: Optional[List[str]] = None):
        super().__init__(chapter_id, title, duration, author_id, collaborator_ids, audio_book_id)

        self.genres = genres
        self.narrator_ids = narrator_ids or [author_id]

    @property
    def get_id(self) -> str:
        return super().get_id

    def serialize(self) -> Dict[str, Any]:
        data = super().serialize()

        data.update({
            "narrator_ids": self.narrator_ids.copy(),
        })

        return data

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'AudioBookChapter':
        return cls(
            chapter_id=data.get("id"),
            title=data.get("title"),
            genres=[AudioBookChapterGenre(genre) for genre in data.get("genres", [])],
            duration=data.get("duration"),
            author_id=data.get("artist_id"),
            collaborator_ids=data.get("collaborator_ids", []),
            narrator_ids=data.get("narrator_ids", []),
            audio_book_id=data.get("source_id")
        )


class MusicPlayer:
    def __init__(self, music_player_id: str, user: User):
        self.music_player_id = music_player_id
        self.user = user

        self.current_track: Optional[Track] = None
        self.current_playlist: Optional[Playlist] = None

        self.is_playing: bool = False

        self.volume: float = 0.8
        self.current_track_position: float = 0.0

        self.shuffle_mode: bool = False
        self.repeat_mode: str = "none"
        self.playback_speed: float = 1.0
        self.equalizer_settings: dict[str, float] = {}

        self.history: list[Track] = []

    @property
    def get_id(self) -> str:
        return self.music_player_id


def full_serialization_test():
    # === 1. Создаём тестовые данные ===

    # Артист
    artist = Artist(
        artist_id="artist_001",
        name="The Rockers",
        email="rockers@mail.com"
    )

    # Альбом артиста
    album = Album(
        album_id="album_001",
        title="Loud & Proud",
        tracks=[],  # заполним позже
        artist_id=artist.get_id
    )

    # Треки артиста
    track1 = Track(
        track_id="track_001",
        title="Thunder Road",
        genres=[TrackGenre.ROCK],
        duration=245.5,
        artist_id=artist.get_id
    )
    track2 = Track(
        track_id="track_002",
        title="Silent Nights",
        genres=[TrackGenre.CLASSIC],
        duration=312.0,
        artist_id=artist.get_id,
        album_id=album.get_id
    )

    # Добавляем треки в альбом и артисту
    album.contents = [track1, track2]
    artist.tracks = [track1, track2]
    artist.albums = [album]

    # Аудиокнига и главы
    chapter1 = AudioBookChapter(
        chapter_id="ch_001",
        title="The Beginning",
        genres=[AudioBookChapterGenre.ROMAN],
        duration=540.0,
        author_id=artist.get_id
    )
    chapter2 = AudioBookChapter(
        chapter_id="ch_002",
        title="The Fear",
        genres=[AudioBookChapterGenre.HORROR],
        duration=666.0,
        author_id=artist.get_id
    )

    audio_book = AudioBook(
        collection_id="book_001",
        title="Story of Sound",
        chapters=[chapter1, chapter2],
        author_id=artist.get_id
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
        owner_id=user.get_id
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

    print(result_user.get_id)


if __name__ == "__main__":
    full_serialization_test()