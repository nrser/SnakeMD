from __future__ import annotations
import os
import pathlib
from typing import Iterable, Union
from urllib.error import HTTPError
from urllib import request


class InlineText:
    """
    The basic unit of text in markdown. All components which contain
    text are built using this class instead of strings directly. That
    way, those elements capture all styling information. 
    """

    def __init__(
        self, 
        text: str, 
        url: str = None, 
        bold: bool = False, 
        italics: bool = False, 
        code: bool = False, 
        image: bool = False
        ) -> None:
        """
        Initialize the inline text object.

        :param text: the inline text to render
        :param url: the link associated with the inline text
        :param bold: the bold state of the inline text; 
            set to True to render bold inline text (i.e., True -> **bold**)
        :param italics: the italics state of the inline text; 
            set to True to render inline text in italics (i.e., True -> *italics*)
        :param code: the italics state of the inline text;
            set to True to render inline text as code (i.e., True -> `code`)
        :param image: the image state of the inline text;
            set to True to render inline text as an image;
            must include url parameter to render
        """
        self.text = text
        self.bold = bold
        self.italics = italics
        self.url = url
        self.code = code
        self.image = image

    def __str__(self) -> str:
        """
        Renders the inline text object as a string. In this case,
        inline text can represent many different types of data from
        stylized text to inline code to links and images. 
        """
        text = self.text
        if self.bold:
            text = f"**{self.text}**"
        elif self.italics:
            text = f"*{self.text}*"
        if self.url:
            text = f"[{text}]({self.url})"
        if self.url and self.image:
            text = f"!{text}"
        if self.code:
            text = f"`{text}`"
        return text

    def _verify_link(self) -> bool:
        """
        Verifies that a URL is a valid URL.

        :return: True if the URL is valid; False otherwise
        """
        req = request.Request(self.url)
        req.get_method = lambda: 'HEAD'
        try:
            request.urlopen(req)
            return True
        except HTTPError:
            return False

    def verify(self) -> bool:
        if self.url:
            assert self._verify_link()

    # TODO: add text processing to avoid issues where asterisks mess up formatting
    # One way to do this would be to backslash special characters in the raw text


class Element:
    """
    An element is defined as a standalone section of a markdown file. 
    All elements are to be surrounded by empty lines. Examples of elements
    include paragraphs, headers, tables, and lists. 
    """

    def __init__(self):
        pass

    def __str__(self) -> str:
        raise NotImplementedError()

    def verify(self):
        raise NotImplementedError()


class Header(Element):
    """
    A header is a text element which serves as the title for a new
    section of a document. Headers come in six main sizes which 
    correspond to the six headers sizes in HTML (e.g., <h1>).
    """

    def __init__(self, text: InlineText, level: int) -> None:
        super().__init__()
        self.text: InlineText = text
        self.level: int = level

    def __str__(self) -> str:
        """
        Renders the header as markdown using the hash mark.

        :return: the header as a markdown string
        """
        return f"{'#' * self.level} {self.text}"

    def promote(self) -> None:
        """
        Promotes a header up a level. Fails silently
        if the header is already at the highest level (i.e., <h1>).

        :return: Nothing
        """
        if self.level > 1:
            self.level -= 1

    def demote(self):
        """
        Demotes a header down a level. Fails silently if
        the header is already at the lowest level (i.e., <h6>).
        """
        if self.level < 6:
            self.level += 1


class Paragraph(Element):
    """
    A paragraph is a standalone element of text. Paragraphs can be
    formatted in a variety of ways including as code and blockquotes. 
    """

    def __init__(self, content: Iterable[InlineText], code=False, lang="generic", quote=False):
        super().__init__()
        self.content = content
        self.code = code
        self.lang = lang
        self.quote = quote

    def __str__(self) -> str:
        paragraph = ' '.join(str(item) for item in self.content)
        if self.code:
            return f"```{self.lang}\n{paragraph}\n```"
        elif self.quote:
            return f"> {paragraph}"
        else:
            return paragraph

    def add(self, text: InlineText):
        self.content.append(text)


class MDList(Element):
    def __init__(self, items: Iterable[Union[InlineText, MDList]], ordered: bool = False) -> None:
        super().__init__()
        self.items: Iterable = items
        self.ordered = ordered
        self.depth = 0

    def __str__(self) -> str:
        output = list()
        i = 1
        for item in self.items:
            if isinstance(item, MDList):
                item.depth = self.depth + 1
                output.append(str(item))
            else:
                if self.ordered:
                    output.append(f"{'  ' * self.depth}{i}. {item}")
                else:
                    output.append(f"{'  ' * self.depth}- {item}")
            i += 1
        return "\n".join(output)


class Table(Element):
    def __init__(self, header: Iterable[InlineText], body: Iterable[Iterable[InlineText]], _footer: Iterable[InlineText] = None) -> None:
        super().__init__()
        self.header = header
        self.body = body
        self.footer = _footer

    def __str__(self) -> str:
        rows = list()
        if self.header:
            rows.append(' | '.join(self.header))
            rows.append(' | '.join("-" for _ in self.header))
        rows.extend(' | '.join(row) for row in self.body)
        if self.footer:
            rows.append(' | '.join("-" for _ in self.footer))
            rows.append(' | '.join(self.footer))
        return '\n'.join(rows)

    def verify(self):
        assert len({len(i) for i in self.body}) == 1
        assert len(self.header) == len(self.footer) == len(self.body[0])


class Document:

    def __init__(self, name: str) -> None:
        self.name = name
        self.ext = ".md"
        self.contents = list()

    def __str__(self):
        return f"{self.name}\n{self._build_page()}"

    def add_element(self, element: Element):
        """
        A generic function for appending elements to the document. 
        Use this function when you want a little more control over
        what the output looks like. 

        :param element: a markdown object (e.g., Table, Header, etc.)
        """
        assert isinstance(element, Element)
        self.contents.append(element)

    def add_header(self, text: str, level: int = 1):
        """
        A convenience method which adds a simple header to the document.

        :param text: the text for the header
        :param level: the level of the header from 1 to 6
        """
        assert 1 <= level <= 6
        self.contents.append(Header(InlineText(text), level))

    def add_paragraph(self, text: str):
        """
        A convenience method which adds a simple paragraph of text to the document.

        :param text: any arbitrary text
        """
        self.contents.append(Paragraph([InlineText(text)]))

    def add_ordered_list(self, items: Iterable[str]):
        """
        A convenience method which adds a simple ordered list to the document. 

        :param items: a "list" of strings
        """
        self.contents.append(MDList((InlineText(item)
                             for item in items), ordered=True))

    def add_unordered_list(self, items: Iterable[str]):
        """
        A convenience method which adds a simple unordered list to the document. 

        :param items: a "list" of strings
        """
        self.contents.append(MDList(InlineText(item) for item in items))

    def add_table(self, grid: Iterable[Iterable[str]], _header: bool = True, _footer: bool = False):
        """
        A convenience method which adds a simple table to the document.

        :param grid: a "list" of "lists" of strings
        """
        head = None
        foot = None
        bounds = [None, None]

        if _header:
            head = grid[0]
            bounds[0] = 1
        if _footer:
            foot = grid[-1]
            bounds[1] = -1

        body = grid[slice(*bounds)]

        self.contents.append(Table(head, body, foot))

    def add_code(self, code: str, lang="generic"):
        """
        A convenience method which adds a code block to the document.

        :param code: a preformatted code string
        """
        self.contents.append(
            Paragraph([InlineText(code)], code=True, lang=lang))

    def add_quote(self, text: str):
        """
        A convenience method which adds a blockquote to the document.

        :param text: the text to be quoted
        """
        self.contents.append(Paragraph([InlineText(text)], quote=True))

    def output_page(self, dump_dir):
        pathlib.Path(dump_dir).mkdir(parents=True, exist_ok=True)
        output_file = open(os.path.join(dump_dir, self._get_file_name()), "w+")
        output_file.write(self._build_page())
        output_file.close()

    def _build_page(self):
        return "\n\n".join(str(element) for element in self.contents)

    def _get_file_name(self):
        separator = "-"
        file_name = f"{separator.join(self.name.split())}{self.ext}"
        return file_name
