#!/usr/bin/env python3
"""
Custom RSS Feed Generator

Pure Python RSS feed generator for podcast feeds without external dependencies
"""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union


class RSSGenerator:
    """Custom RSS feed generator for podcast feeds."""

    def __init__(self):
        """Initialize the RSS generator."""
        self.channel_data = {}
        self.items = []

    def set_channel_info(
        self,
        title: str,
        description: str,
        link: str,
        language: str = "en-US",
        author: str = "",
        category: str = "News",
        owner_name: str = "",
        owner_email: str = "",
        explicit: bool = False,
    ) -> None:
        """Set the channel metadata for the RSS feed.

        Args:
            title: Channel title
            description: Channel description
            link: Channel link/URL
            language: Language code (default: en-US)
            author: Author name
            category: iTunes category
            owner_name: Owner name for iTunes
            owner_email: Owner email for iTunes
            explicit: Whether content is explicit
        """
        self.channel_data = {
            "title": title,
            "description": description,
            "link": link,
            "language": language,
            "author": author,
            "category": category,
            "owner_name": owner_name,
            "owner_email": owner_email,
            "explicit": "yes" if explicit else "no",
        }

    def add_episode(
        self,
        title: str,
        description: str,
        audio_url: str,
        audio_size: int,
        duration: str,
        pub_date: Union[datetime, str],
        guid: Optional[str] = None,
    ) -> None:
        """Add an episode to the RSS feed.

        Args:
            title: Episode title
            description: Episode description
            audio_url: URL to audio file
            audio_size: Size of audio file in bytes
            duration: Duration in HH:MM:SS format
            pub_date: Publication date as datetime or string
            guid: GUID for episode (uses audio_url if not provided)
        """
        if isinstance(pub_date, str):
            # Parse string date in YYYY-MM-DD format
            pub_date = datetime.strptime(pub_date, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        elif not pub_date.tzinfo:
            pub_date = pub_date.replace(tzinfo=timezone.utc)

        episode = {
            "title": title,
            "description": description,
            "audio_url": audio_url,
            "audio_size": audio_size,
            "duration": duration,
            "pub_date": pub_date,
            "guid": guid or audio_url,
        }
        self.items.append(episode)

    def generate_xml(self) -> str:
        """Generate the RSS XML feed as a string.

        Returns:
            RSS XML content as string
        """
        # Create root RSS element
        rss = ET.Element("rss")
        rss.set("version", "2.0")
        rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
        rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
        rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")

        # Create channel element
        channel = ET.SubElement(rss, "channel")

        # Add channel metadata
        ET.SubElement(channel, "title").text = self.channel_data.get("title", "")
        ET.SubElement(channel, "link").text = self.channel_data.get("link", "")
        ET.SubElement(channel, "description").text = self.channel_data.get(
            "description", ""
        )

        # Add atom:link for self-reference
        atom_link = ET.SubElement(channel, "atom:link")
        atom_link.set("href", self.channel_data.get("link", ""))
        atom_link.set("rel", "self")

        # Add RSS specification docs
        ET.SubElement(
            channel, "docs"
        ).text = "http://www.rssboard.org/rss-specification"

        # Add language
        ET.SubElement(channel, "language").text = self.channel_data.get(
            "language", "en-US"
        )

        # Add last build date (current time)
        last_build_date = datetime.now(timezone.utc).strftime(
            "%a, %d %b %Y %H:%M:%S %z"
        )
        ET.SubElement(channel, "lastBuildDate").text = last_build_date

        # Add iTunes-specific elements
        if self.channel_data.get("author"):
            ET.SubElement(channel, "itunes:author").text = self.channel_data["author"]

        if self.channel_data.get("category"):
            itunes_category = ET.SubElement(channel, "itunes:category")
            itunes_category.set("text", self.channel_data["category"])

        ET.SubElement(channel, "itunes:explicit").text = self.channel_data.get(
            "explicit", "no"
        )

        # Add owner information if provided
        if self.channel_data.get("owner_name") and self.channel_data.get("owner_email"):
            owner = ET.SubElement(channel, "itunes:owner")
            ET.SubElement(owner, "itunes:name").text = self.channel_data["owner_name"]
            ET.SubElement(owner, "itunes:email").text = self.channel_data["owner_email"]

        if self.channel_data.get("description"):
            ET.SubElement(channel, "itunes:summary").text = self.channel_data[
                "description"
            ]

        # Add episodes
        for episode in self.items:
            item = ET.SubElement(channel, "item")

            ET.SubElement(item, "title").text = episode["title"]
            ET.SubElement(item, "description").text = episode["description"]

            # Add GUID
            guid = ET.SubElement(item, "guid")
            guid.set("isPermaLink", "false")
            guid.text = episode["guid"]

            # Add enclosure (audio file)
            enclosure = ET.SubElement(item, "enclosure")
            enclosure.set("url", episode["audio_url"])
            enclosure.set("length", str(episode["audio_size"]))
            enclosure.set("type", "audio/mpeg")

            # Add publication date
            pub_date_str = episode["pub_date"].strftime("%a, %d %b %Y %H:%M:%S %z")
            ET.SubElement(item, "pubDate").text = pub_date_str

            # Add iTunes-specific episode elements
            ET.SubElement(item, "itunes:duration").text = episode["duration"]
            ET.SubElement(item, "itunes:summary").text = episode["description"]

        # Convert to string with pretty formatting
        self._indent(rss)
        xml_str = ET.tostring(rss, encoding="unicode", xml_declaration=False)

        # Add XML declaration manually for better control
        return f"<?xml version='1.0' encoding='UTF-8'?>\n{xml_str}\n"

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save the RSS feed to a file.

        Args:
            file_path: Path to save the XML file
        """
        xml_content = self.generate_xml()

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(xml_content)

    def _indent(self, elem: ET.Element, level: int = 0) -> None:
        """Add pretty-printing indentation to XML elements.

        Args:
            elem: XML element to indent
            level: Current indentation level
        """
        indent = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                self._indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent


def create_podcast_rss(
    title: str,
    description: str,
    link: str,
    author: str,
    owner_email: str,
    episodes: List[Dict],
    output_path: Union[str, Path],
) -> str:
    """Create a podcast RSS feed with the given parameters.

    Args:
        title: Podcast title
        description: Podcast description
        link: Podcast link/URL
        author: Author name
        owner_email: Owner email address
        episodes: List of episode dictionaries
        output_path: Path to save the XML file

    Returns:
        Path to the generated RSS file
    """
    generator = RSSGenerator()

    # Set channel information
    generator.set_channel_info(
        title=title,
        description=description,
        link=link,
        author=author,
        owner_name=author,
        owner_email=owner_email,
    )

    # Add episodes
    for episode in episodes:
        generator.add_episode(
            title=episode["title"],
            description=episode["description"],
            audio_url=episode["audio_url"],
            audio_size=episode["audio_size"],
            duration=episode["duration"],
            pub_date=episode["pub_date"],
            guid=episode.get("guid"),
        )

    # Save to file
    generator.save_to_file(output_path)

    return str(output_path)
