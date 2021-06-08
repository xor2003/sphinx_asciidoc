#!/bin/python
# -*- coding: utf-8 -*-

"""
   sphinx.writers.asciidoc
   ~~~~~~~~~~~~~~~~~~~~~~~

   Custom docutils writer for AsciiDoc format.

   This writer is based on the RTF writer by Benoit Allard (benoit@aeteurope.nl) and has been adapted to use with AsciiDoc.

   Author:    Lukas Ruzicka
   Contact:   lukas.ruzicka@gmail.com
   Copyright: This module has been placed in the public domain.
"""
from docutils import writers, nodes
import sys, os, json

from sphinx import addnodes
from docutils.core import publish_parts, publish_from_doctree
from sphinx.locale import admonitionlabels, _


class AsciiDocWriter(writers.Writer):

    supported = ("asciidoc",)
    output = None

    def __init__(self):
        writers.Writer.__init__(self)
        self._translator_class = AsciiDocTranslator

    def translate(self):
        visitor = self._translator_class(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()


def toansi(text):
    """Encode special characters"""
    trans = {
        "{": r"\{",
        "}": r"\}",
        "\\": r"\\",
        "|": r"\|",
    }
    out = ""
    for char in text:
        if char in trans:
            out += trans[char]
        elif ord(char) < 127:
            out += char
        else:
            out += r"\'%x" % ord(char)
    return out


sectionEquals = {  # Stores values for different section levels
    -1: "",
    0: "=",  # Document Title (Level 0)
    1: "==",  # Level 1 Section Title
    2: "===",  # Level 2 Section Title
    3: "====",  # Level 3 Section Title
    4: "=====",  # Level 4 Section Title
    5: "======",  # Level 5 Section Title
}


bulletIndent = {  # Adds indentation to bullet lists
    1: "* ",  # First level
    2: "** ",  # Second level
    3: "*** ",  # Third level
    4: "**** ",  # Fourth level
    5: "***** ",  # Fifth level
}

enumIndent = {  # Adds indentation to ordered lists
    1: ". ",  # First level
    2: ".. ",  # Second level
    3: "... ",  # Third level
    4: ".... ",  # Fourth level
    5: "..... ",  # Fifth level
}

numberIndent = {}  # Holds the level of indentation


def indent(fn):
    def wrapper(self, *args, **kwargs):
        self.par_level += 1
        return fn(self, *args, **kwargs)

    return wrapper


def dedent(fn):
    def wrapper(self, *args, **kwargs):
        self.par_level -= 1
        return fn(self, *args, **kwargs)

    return wrapper


class AsciiDocTranslator(nodes.NodeVisitor):
    def __init__(self, document):
        nodes.NodeVisitor.__init__(self, document)
        self.body = []
        self.section_level = 0
        self.par_level = -1

        # stack of the currents bullets
        self.lists = []
        self.listLevel = len(self.lists)
        # next one to add to the next paragraph
        self.bullet = "*"
        # Counts figures for reference targets
        self.figures = 0
        self.images = 0
        self.idcount = 0
        self.inTable = False
        self.turnsInList = 0
        self.inDesc = False
        self.inList = False
        self.inField = False
        self.inImgLink = False
        self.inFigure = False
        self.lastFigure = {"image": "", "caption": "", "legend": "", "ref": ""}
        self.inTopicContents = False
        self.extLinkActive = False
        self.inAdmonition = False
        self.tabColSpecs = []
        self.inLineBlock = False
        self.inLiteralBlock = False
        self.inToctree = False
        self.inUseless = False
        self.inGlossary = False
        self.sourceFile = ""
        self.idPool = []

        #
        # Things that should be options, but aren't
        #
        # Output the rendered TOC from docutils, or just `:toc:`
        self.outputTOC = False
        # Table column alignment, if not specified. Can be <>^ or
        # '' for unspecified.
        self.defaultTableColAlign = ""
        # Specify percentages for columns widths, or leave browser to auto-layout?
        self.defaultTableColWidths = False

    def astext(self):
        try:
            return "".join(self.body)
        except UnicodeDecodeError:
            pass

    def visit_document(self, node):
        source = node.get("source").split("/")
        source = source[-1].split(".")
        self.sourceFile = source[0]

        # try:
        #    with open('idPool.temp') as pool:
        #        self.idPool = json.load(pool)
        #        print('File opened')
        # except:
        #    self.idPool = []
        pass

    def depart_document(self, node):
        # with open('idPool.temp','w') as pool:
        #    json.dump(self.idPool, pool)
        #    print('File created')
        pass

    def visit_title(self, node):
        if self.inTopicContents and not self.outputTOC:
            pass
        elif isinstance(node.parent, nodes.document):
            """doc title"""
            self.body.append("\n\n%s " % sectionEquals[0])
        elif isinstance(node.parent, nodes.section):
            level = self.section_level
            try:
                tstr = sectionEquals[level]
            except KeyError:
                tstr = "= "
            self.body.append("\n%s " % tstr)
        elif isinstance(node.parent, nodes.table):
            self.body.append("\n.")  # Table title

    def depart_title(self, node):
        if self.inTopicContents and not self.outputTOC:
            pass
        elif isinstance(node.parent, nodes.table):
            self.body.append("\n")  # Table title
        else:
            self.body.append("\n")

    def visit_Text(self, node):
        ##        if self.bullet is not None:
        ##            self.body.append(self.bullet+'')
        ##            self.bullet = None
        ##        self.body.append(toansi(node.astext()))
        if self.inTopicContents and not self.outputTOC:
            pass
        elif self.inFigure:
            # Figures are all handled in depart_figure, so skip
            pass
        else:
            if self.inLineBlock == True:
                self.body.append(node.astext() + " +")
            else:
                self.body.append(node.astext())

    def depart_Text(self, node):
        pass

    def visit_strong(self, node):  # Does the bold face
        self.body.append("*")

    def depart_strong(self, node):
        self.body.append("*")

    def visit_index(self, node):  # FIXME
        entrylist = node.get("entries")
        entries = entrylist[0]
        term = entries[1]
        description = entries[2]
        self.body.append(" [[%s]]" % description)
        pass

    def depart_index(self, node):
        # self.body.append('\n')
        pass

    def visit_section(self, node):
        self.section_level += 1

    def depart_section(self, node):
        self.section_level -= 1

    @indent
    def visit_paragraph(self, node):
        if self.inDesc == True:
            nline = ""
        elif self.inField == True:
            nline = ""
        elif self.inTable == True or self.inList == True:
            nline = ""
        elif self.inTopicContents and not self.outputTOC:
            nline = ""
        else:
            nline = "\n"
        self.body.append(nline)

    @dedent
    def depart_paragraph(self, node):
        if self.listLevel == -1:
            nline = "\n\n"
        elif self.inTable == True:
            nline = ""
        elif self.inField == True:
            nline = ""
        elif self.inTopicContents and not self.outputTOC:
            nline = ""
        else:
            nline = "\n"
        self.body.append(nline)

    def visit_compact_paragraph(self, node):
        self.body.append("")

    @dedent
    def depart_compact_paragraph(self, node):
        if self.listLevel == -1:
            nline = "\n\n"
        else:
            nline = "\n"
        self.body.append(nline)

    def visit_bullet_list(self, node):  # Unordered list
        if self.inTopicContents and not self.outputTOC:
            pass
        else:
            self.inList = True
            self.lists.append("bulleted")
            if self.turnsInList == 0:
                self.body.append("\n")
            self.turnsInList += 1

    def depart_bullet_list(self, node):
        if self.inTopicContents and not self.outputTOC:
            pass
        else:
            self.body.append("\n")
            self.lists.pop(-1)
            self.turnsInList -= 1
            if self.turnsInList <= 0:
                self.inList = False

    def visit_enumerated_list(self, node):  # Ordered list
        if self.turnsInList == 0:
            enumeration = node["enumtype"]
        else:
            enumeration = False
        self.inList = True
        self.lists.append("numbered")
        if enumeration != False:
            self.body.append("\n[" + enumeration + "]\n")
        self.turnsInList += 1

    def depart_enumerated_list(self, node):
        self.lists.pop(-1)
        self.turnsInList -= 1
        if self.turnsInList <= 0:
            self.inList = False

    def visit_list_item(self, node):
        if self.inTopicContents and not self.outputTOC:
            pass
        else:
            classes = node.get("classes")
            level = len(self.lists)

            if "toctree" in str(classes):
                nline = ""
            elif "bulleted" in self.lists:
                nline = bulletIndent[level]
            elif "numbered" in self.lists:
                nline = enumIndent[level]
            else:
                nline = "\nList indentation error!\n"
            self.body.append(nline)
            # self.turnsInList = self.turnsInList + 1

    def depart_list_item(self, node):
        if self.inTopicContents and not self.outputTOC:
            pass
        elif self.inTable == True:
            self.body.append("")
        else:
            self.body.append("\n")

    def visit_block_quote(self, node):
        pass

    def depart_block_quote(self, node):
        pass

    def visit_toctree(self, node):
        pass

    def depart_toctree(self, node):
        pass

    def visit_reference(self, node):
        self.extLinkActive = True
        uri = node.get("refuri")
        refid = node.get("refid")
        name = node.get("name")
        aname = node.get("anchorname")
        internal = node.get("internal")
        self.linkType = None

        for n in node.traverse(include_self=False):
            ns = str(n)

        if ns.startswith("<image"):
            # Link wraps an image. Needs to come out in
            # the opposite order: link, then image
            self.inImgLink = True

        if self.inTopicContents and not self.outputTOC:
            pass
        elif self.inFigure:
            # Figures are all handled in depart_figure, so skip
            pass
        elif self.inImgLink:
            self.body.append(f"\n[link::{uri}]")

        elif self.inLiteralBlock:
            pass
        elif internal == True and aname == "" and self.inToctree == True:
            self.linkType = "include"
            self.body.append(f"include::{uri}[leveloffset=+1][")
        elif uri and name:
            self.linkType = "link"
            # Make an attempt to only use the link macro if needed
            print(uri)
            if (
                any(x in uri for x in [" ", "^", "__"])
                or uri.startswith("{filename}")
                or uri.startswith("/")
            ):
                nline = f"link:++{uri}["
            else:
                nline = f"{uri}["
            self.body.append(nline)
        elif refid:
            self.linkType = "refx"
            if self.inToctree == False:
                self.body.append(f"xref:{refid}[")
            else:
                pass
        elif uri:
            self.linkType = "refx"
            try:
                uri = uri.split("#")
                uri = uri[1]
            except IndexError:
                uri = str(uri[0])
            if ".adoc" in uri:
                self.body.append(f"xref:fileref={uri}[")
            else:
                if uri.startswith("mailto") or uri.startswith("http"):
                    self.body.append(f"{uri}[")
                else:
                    if aname == ("#" + str(uri)):
                        self.body.append("\n//")
                        self.inUseless = True
                    else:
                        self.body.append(f"xref:{uri}[")
        else:
            pass
            # print(node)

    def depart_reference(self, node):
        if self.inTopicContents and not self.outputTOC:
            pass
        elif self.inFigure:
            # Figures are all handled in depart_figure, so skip
            pass
        elif self.inImgLink:
            self.inImgLink = False

        elif self.inLiteralBlock is False:
            self.body.append("]")

    def visit_docinfo(self, node):
        # self.body.append('Document information: ')
        self.body.append("")

    def depart_docinfo(self, node):
        self.body.append("\n\n")

    def visit_author(self, node):
        self.body.append("Author: ")

    def depart_author(self, node):
        self.body.append("\n\n")

    def visit_version(self, node):
        self.body.append("Document version: ")

    def depart_version(self, node):
        self.body.append("\n\n")

    def visit_copyright(self, node):
        self.body.append("Copyright: ")

    def depart_copyright(self, node):
        self.body.append("\n\n")

    def visit_rubric(
        self, node
    ):  # This holds a place for some listings, such as footnotes.
        self.body.append("\n")
        self.body.append(".")

    def depart_rubric(self, node):
        self.body.append("\n")

    def visit_topic(self, node):
        if str(node).startswith('<topic classes="contents" ids="contents"'):
            # This is the `.. contents:: Contents:` topic
            self.inTopicContents = True
            self.body.append(":toc:")
        else:
            pass

    def depart_topic(self, node):
        self.inTopicContents = False
        self.body.append("\n")

    def visit_sidebar(self, node):
        self.body.append("****\n")

    def depart_sidebar(self, node):
        self.body.append("****")

    def visit_target(self, node):
        # Create internal inline links.
        try:
            refid = node.get("refid")
            ids = node.get("ids")
            refuri = node.get("refuri")
        except IndexError:
            self.idcount += 1
            refid = "automatic-id%s" % self.idcount
        if refid:
            while True:
                if refid not in self.idPool:
                    self.body.append('[id="%s"]' % refid)
                    self.idPool.append(refid)
                    break
                else:
                    refid = refid + "-duplicate"
                    self.body.append('[id="%s"]' % refid)
        elif ids and refuri:
            self.body.append("")
        else:
            print("Warning: Problem with targets!")
            self.body.append("Warning: Problem with targets!")

    def depart_target(self, node):
        self.body.append("")

    def visit_compound(self, node):
        self.inToctree = True
        self.body.append("")

    def depart_compound(self, node):
        self.body.append("\n")
        self.inToctree = False

    def visit_glossary(self, node):  # It seems that this can be passed.
        self.inGlossary = True

    def depart_glossary(self, node):
        self.inGlossary = False

    def visit_note(self, node):
        self.inAdmonition = True
        if self.inList == True:
            nline = "+\n[NOTE]\n"
        else:
            nline = "\n[NOTE]\n"
        mline = "====\n"
        self.body.append(nline + mline)

    def depart_note(self, node):
        if self.inList == True:
            nline = "====\n\n"
        else:
            nline = "====\n"
        self.body.append(nline)
        self.inAdmonition = False

    def visit_literal(self, node):
        self.body.append("`")

    def depart_literal(self, node):
        self.body.append("`")

    def visit_literal_strong(self, node):
        self.body.append("`*")

    def depart_literal_strong(self, node):
        self.body.append("*`")

    def visit_literal_block(self, node):
        self.inLiteralBlock = True

        cls = node.attributes.get("classes")
        lang = None
        if cls and cls[0] == "code":
            lang = cls[1]

        level = len(self.lists)
        attributes = []
        block_char = "----"
        if "language" in node.attributes:
            attributes += ["source", node.attributes["language"]]
        elif lang:
            attributes += ["source", lang]

        if "linenos" in node.attributes and node.attributes["linenos"] is True:
            attributes.append("linenums")
        if self.inAdmonition == True:
            nline = block_char
        elif level > 0:
            nline = "+" + block_char
        else:
            nline = block_char
        # attributes.append('sub="attributes"')
        self.body.append("\n[" + ",".join(attributes) + "]\n" + nline + "\n")

    def depart_literal_block(self, node):
        self.body.append("\n----\n")
        self.inLiteralBlock = False

    def visit_emphasis(self, node):
        self.body.append(" _")

    def depart_emphasis(self, node):
        self.body.append("_")

    def visit_literal_emphasis(self, node):
        self.body.append(" `*")

    def depart_literal_emphasis(self, node):
        self.body.append("*`")

    def visit_tip(self, node):
        self.inAdmonition = True
        if self.inList == True:
            nline = "+\n[TIP]\n"
        else:
            nline = "\n[TIP]\n"
        mline = "====\n"
        self.body.append(nline + mline)

    def depart_tip(self, node):
        if self.inList == True:
            nline = "====\n\n"
        else:
            nline = "====\n"
        self.body.append(nline)
        self.inAdmonition = False

    def visit_warning(self, node):
        self.inAdmonition = True
        if self.inList == True:
            nline = "+\n[WARNING]\n"
        else:
            nline = "\n[WARNING]\n"
        mline = "====\n"
        self.body.append(nline + mline)

    def depart_warning(self, node):
        if self.inList == True:
            nline = "====\n\n"
        else:
            nline = "====\n"
        self.body.append(nline)
        self.inAdmonition = False

    def visit_subtitle(self, node):
        self.body.append("")

    def depart_subtitle(self, node):
        self.body.append("")

    def visit_attribution(self, node):
        self.body.append("-- ")

    def depart_attribution(self, node):
        self.body.append("\n")

    def visit_important(self, node):
        self.inAdmonition = True
        if self.inList == True:
            nline = "+\n[IMPORTANT]\n"
        else:
            nline = "\n[IMPORTANT]\n"
        mline = "====\n"
        self.body.append(nline + mline)

    def depart_important(self, node):
        if self.inList == True:
            nline = "====\n\n"
        else:
            nline = "====\n"
        self.body.append(nline)
        self.inAdmonition = False

    def visit_caution(self, node):
        self.inAdmonition = True
        if self.inList == True:
            nline = "+\n[CAUTION]\n"
        else:
            nline = "\n[CAUTION]\n"
        mline = "====\n"
        self.body.append(nline + mline)

    def depart_caution(self, node):
        # FIXME: change to level = len(self.lists)
        if self.inList == True:
            nline = "====\n\n"
        else:
            nline = "====\n"
        self.body.append(nline)
        self.inAdminition = False

    def visit_definition_list(self, node):
        self.body.append("\n")

    def depart_definition_list(self, node):
        self.body.append("\n")

    def visit_definition_list_item(self, node):
        self.body.append("")

    def depart_definition_list_item(self, node):
        self.body.append("\n")

    def visit_term(self, node):
        if self.inGlossary == True:
            self.section_level += 1
            try:
                tstr = sectionEquals[self.section_level]
            except KeyError:
                tstr = "= "
            self.body.append("\n\n%s " % tstr)
        else:
            nline = ""
            self.body.append(nline)

    def depart_term(self, node):
        if self.inGlossary == True:
            self.body.append("\n\n")
        else:
            self.body.append(":: ")

    def visit_definition(self, node):
        self.body.append("\n")

    def depart_definition(self, node):
        self.body.append("\n\n")
        if self.inGlossary == True:
            self.section_level -= 1

    def visit_image(self, node):
        if self.inFigure:
            # Figures are all handled in depart_figure, so skip
            pass
        else:
            try:
                alt = node.get("alt")
                if alt == None:
                    alt = ""
            except KeyError:
                alt = ""

            uri = node.get("uri")
            self.body.append("\nimage::{}[{}]".format(uri, alt))

    def depart_image(self, node):
        if self.inFigure:
            # Figures are all handled in depart_figure, so skip
            pass
        else:
            self.body.append("\n\n")

    def visit_footnote_reference(self, node):
        try:
            ref = str(node.get("refid")[0])
            nline = "footnoteref:[" + ref + ","
        except KeyError:
            pass
        self.body.append(nline)

    def depart_footnote_reference(self, node):
        self.body.append("] ")

    def visit_footnote(self, node):
        pass

    def depart_footnote(self, node):
        self.body.append("\n")

    def visit_label(self, node):
        self.body.append("[[*")

    def depart_label(self, node):
        self.body.append("*]]")

    def visit_contents(self, node):
        self.body.append("== ")

    def depart_contents(self, node):
        pass

    def visit_system_message(self, node):
        self.body.append("\n// System message: ")

    def depart_system_message(self, node):
        # self.body.append('')
        pass

    # Figures in AsciiDoc have their elements in a different
    # order to the source rst, as well as having a different syntax.
    # This means that we need to buffer the figure into self.lastFigure,
    # then output the elements in the correct order & format in the
    # depart_figure.
    def visit_figure(self, node):
        self.inFigure = True
        for n in node.traverse(include_self=False):
            ns = str(n)
            # Stash figure parts in self.lastFigure
            # FIXME: I'm sure there's a better way to figure
            # out what the element is than startswith.
            if ns.startswith("<image"):
                self.lastFigure["image"] = n
            elif ns.startswith("<caption"):
                self.lastFigure["caption"] = n
            elif ns.startswith("<legend"):
                self.lastFigure["legend"] = n
            elif ns.startswith("<reference"):
                self.lastFigure["ref"] = n

    # FIXME: I'm sure there's a better way to do this, triggering a visit for
    # the elements in the order we want, rather than just outputting it
    # all in here? Maybe self.displatch_visit(node)?
    def depart_figure(self, node):
        if self.lastFigure["caption"] or self.lastFigure["legend"]:
            try:
                cap = self.lastFigure["caption"].astext()
            except AttributeError:
                cap = ""

            try:
                leg = self.lastFigure["legend"].astext()
            except AttributeError:
                leg = ""

            if cap.startswith("."):
                cap = "\{}".format(cap)

            self.body.append(
                "\n.{} {}\n".format(
                    cap,
                    leg,
                )
            )
        if self.lastFigure["ref"]:
            self.body.append("[link={}]\n".format(self.lastFigure["ref"].get("refuri")))
        if self.lastFigure["image"]:
            self.body.append(
                "image::{}[{}]\n".format(
                    self.lastFigure["image"].get("uri"),
                    str(self.lastFigure["image"].get("alt") or ""),
                )
            )

        self.inFigure = False
        self.lastFigure = {"image": "", "caption": "", "legend": "", "ref": ""}

    def visit_caption(self, node):
        if self.inFigure:
            # Figures are all handled in depart_figure, so skip
            pass
        else:
            self.body.append("\n:toctitle: ")

    def depart_caption(self, node):
        if not self.inFigure:
            self.body.append("\n\n")

    def visit_legend(self, node):
        if not self.inFigure:
            self.body.append("LEGEND:")

    def depart_legend(self, node):
        if not self.inFigure:
            self.body.append(":LEGEND")

    ## Whole table element
    def visit_table(self, node):
        self.inTable = True

    def depart_table(self, node):
        self.inTable = False

    ## Whole inside of the table
    def visit_tgroup(self, node):
        cols = node["cols"]
        specs = self.tabColSpecs

        # Figure out column widths & table width in chars
        clist = []
        if self.defaultTableColWidths:
            tableWidth = 0
            for n in node.traverse(include_self=False):
                ns = str(n)
                if ns.startswith("<colspec"):
                    clist.append(n["colwidth"])
                    tableWidth += n["colwidth"]
            # Convert col widths to percentages
            clist = [round(c / tableWidth * 100) for c in clist]

        # Create a default alignment spec for each column
        if specs == []:
            specs = [
                self.defaultTableColAlign,
            ] * cols

        # If there are col specs in the source, update the default column specs
        for spec in specs:
            i = specs.index(spec)
            if str(spec).lower() == "r":
                specs[i] = ">"
            elif str(spec).lower() == "c":
                specs[i] = "^"
            elif type(spec) != int:
                specs[i] = self.defaultTableColAlign

        # Figure out table header line
        cline = ""
        sep = ","
        for i in range(len(clist)):
            if i == len(clist) - 1:
                sep = ""

            cline = "{}{}{}%{}".format(cline, specs[i], clist[i], sep)

        if cline:
            specline = '[cols="' + cline + '",options="header"]\n'
        else:
            specline = '[options="header"]\n'

        introline = "|===\n"
        self.body.append(specline + introline)

    def depart_tgroup(self, node):
        nline = "|===\n"
        self.body.append(nline)

    ## Column specifics
    def visit_colspec(self, node):
        pass

    def depart_colspec(self, node):
        pass

    ## Column specifics
    def visit_tabular_col_spec(self, node):
        specs = node.get("spec").split("|")
        del specs[-1]
        del specs[0]
        self.tabColSpecs = specs

    def depart_tabular_col_spec(self, node):
        pass

    ## Table head
    def visit_thead(self, node):
        pass

    def depart_thead(self, node):
        pass

    # Table row
    def visit_row(self, node):
        pass

    def depart_row(self, node):
        self.body.append("\n")

    # Table cell
    def visit_entry(self, node):
        self.body.append("|")

    def depart_entry(self, node):
        pass

    def visit_tbody(self, node):
        pass

    def depart_tbody(self, node):
        pass

    def visit_subscript(self, node):
        self.body.append("~")

    def depart_subscript(self, node):
        self.body.append("~")

    def visit_superscript(self, node):
        self.body.append("^")

    def depart_superscript(self, node):
        self.body.append("^")

    def visit_title_reference(
        self, node
    ):  # This, in rst, was rendered as typeface font only.
        self.body.append("`*")

    def depart_title_reference(self, node):
        self.body.append("*`")

    def visit_line_block(self, node):
        self.inLineBlock = True
        self.body.append("\n")

    def depart_line_block(self, node):
        self.body.append(" ")
        self.inLineBlock = False

    def visit_line(self, node):
        nlink = ""
        self.body.append(nlink)

    def depart_line(self, node):
        self.body.append("\n")

    def visit_comment(self, node):
        self.body.append("\n////\n")

    def depart_comment(self, node):
        self.body.append("\n////\n\n")

    def visit_problematic(
        self, node
    ):  # Occurs when the rst source files have an error in them.
        self.body.append("*Problematic*, check error messages! : ")

    def depart_problematic(self, node):
        self.body.append("")

    def visit_meta(self, node):
        name = str(node.get("name"))
        content = str(node.get("content"))
        self.body.append(":" + name + ":" + " " + content)

    def depart_meta(self, node):
        self.body.append("\n")

    def visit_transition(self, node):
        self.body.append("\n* * *")

    def depart_transition(self, node):
        self.body.append("\n")

    def visit_manpage(self, node):
        self.body.append("_")

    def depart_manpage(self, node):
        self.body.append("_")
        pass

    def visit_raw(self, node):
        self.body.append("RAW: ")

    def depart_raw(self, node):
        self.body.append("")

    def visit_subtitle(self, node):
        self.body.append("SUBTITLE: ")

    def depart_subtitle(self, node):
        self.body.append("")

    def visit_inline(self, node):  # Leave passed
        pass

    def depart_inline(self, node):
        pass

    def visit_desc(self, node):
        self.inDesc = True
        self.body.append("\n")

    def depart_desc(self, node):
        self.inDesc = False
        self.body.append("\n")

    def visit_desc_signature(self, node):
        self.body.append("DESCSIGNATURE: ")

    def depart_desc_signature(self, node):
        self.body.append(":DESCSIGNATURE")

    def visit_desc_signature_line(self, node):
        self.body.append("DESCSIGLINE:")

    def depart_desc_signature_line(self, node):
        self.body.append("DESCSIGLINE")

    def visit_desc_name(self, node):
        self.body.append("DESCNAME:")

    def depart_desc_name(self, node):
        self.body.append(":DESCNAME")

    def visit_desc_addname(self, node):
        self.body.append("DESCADDNAME")

    def depart_desc_addname(self, node):
        self.body.append(":DESCADDNAME")

    def visit_desc_type(self, node):
        self.body.append("DESCTYPE:")

    def depart_desc_type(self, node):
        self.body.append(":DESCTYPE")

    def visit_desc_returns(self, node):
        self.body.append("DESCRETURNS:")

    def depart_desc_returns(self, node):
        self.body.append(":DESCRETURNS")

    def visit_desc_parameterlist(self, node):
        self.body.append("DESCPARALIST:")

    def depart_desc_parameterlist(self, node):
        self.body.append(":DESCPARALIST")

    def visit_desc_parameter(self, node):
        self.body.append("DESCPARAMETER:")

    def depart_desc_parameter(self, node):
        self.body.append(":DESCPARAMETER")

    def visit_desc_optional(self, node):
        self.body.append(":DESCOPTIONAL")

    def depart_desc_optional(self, node):
        self.body.append("DESCOPTIONAL:")

    def visit_desc_annotation(self, node):
        self.body.append(":DESCANNOTATION")

    def depart_desc_annotation(self, node):
        self.body.append("DESCANNOTATION:")

    def visit_desc_content(self, node):
        self.body.append(":DESCCONTENT")

    def depart_desc_content(self, node):
        self.body.append("DESCCONTENT:")

    def visit_productionlist(self, node):
        #   self.new_state()
        #   names = []
        #  for production in node:
        #      names.append(production['tokenname'])
        #  maxlen = max(len(name) for name in names)
        #  lastname = None
        #  for production in node:
        #      if production['tokenname']:
        #          self.add_text(production['tokenname'].ljust(maxlen) + ' ::=')
        #          lastname = production['tokenname']
        #      elif lastname is not None:
        #          self.add_text('%s    ' % (' ' * len(lastname)))
        #      self.add_text(production.astext() + self.nl)
        #  self.end_state(wrap=False)
        #  raise nodes.SkipNode
        self.body.append("PRODUCTIONLIST:")

    def depart_production_list(self, node):
        self.body.append(":PRODUCTIONLIST")

    def visit_option_list(self, node):
        pass

    def depart_option_list(self, node):
        self.body.append("\n")

    def visit_option_list_item(self, node):
        pass

    def depart_option_list_item(self, node):
        pass

    def visit_option_group(self, node):
        self.body.append("")

    def depart_option_group(self, node):
        self.body.append("")

    def visit_option(self, node):
        pass

    def depart_option(self, node):
        pass

    def visit_option_string(self, node):
        self.body.append("")

    def depart_option_string(self, node):
        self.body.append(" ")

    def visit_option_argument(self, node):
        self.body.append("")

    def depart_option_argument(self, node):
        self.body.append(" ")

    def visit_description(self, node):
        self.body.append(":: ")

    def depart_description(self, node):
        self.body.append("\n")

    def visit_field_list(self, node):
        self.body.append("\n|===\n")

    def depart_field_list(self, node):
        self.body.append("|===\n")

    def visit_field(self, node):
        self.body.append("")

    def depart_field(self, node):
        self.body.append("\n")

    # Metadata fields
    def visit_field_name(self, node):
        self.body.append(":")

    def depart_field_name(self, node):
        self.body.append(": ")

    def visit_field_body(self, node):
        self.inField = True

    def depart_field_body(self, node):
        self.inField = False

    def visit_centered(self, node):
        self.body.append("CENTER:")

    def depart_centered(self, node):
        self.body.append(":CENTER")

    def visit_hlist(self, node):
        self.body.append("")

    def depart_hlist(self, node):
        self.body.append("")

    def visit_hlistcol(self, node):
        self.body.append("")

    def depart_hlistcol(self, node):
        self.body.append("")

    def visit_versionmodified(self, node):
        self.body.append("")

    def depart_versionmodified(self, node):
        self.body.append("")

    def visit_date(self, node):
        self.body.append(":date: ")

    def depart_date(self, node):
        self.body.append("\n")

    def visit_revision(self, node):
        self.body.append("Revision:")

    def depart_revision(self, node):
        self.body.append(":Revision")

    def visit_doctest_block(self, node):
        self.body.append("DocTestBlok:")

    def depart_doctest_block(self, node):
        self.body.append(":DocTestBlok")

    def visit_classifier(self, node):
        self.body.append("Classifier:")

    def depart_classifier(self, node):
        self.body.append(":Classifier")

    def visit_citation(self, node):
        self.body.append("")

    def depart_citation(self, node):
        self.body.append("")

    def visit_citation_reference(self, node):
        self.body.append("CitationRFR:")

    def depart_citation_reference(self, node):
        self.body.append(":CitationRFR")

    def visit_substitution_definition(self, node):
        name = node.get("names")[0]
        self.body.append("\n:" + name + ": ")

    def depart_substitution_definition(self, node):
        self.body.append("\n")

    def visit_abbreviation(self, node):
        pass  # FIXME: We lose explanation this way

    def depart_abbreviation(self, node):
        pass  # FIXME: We lose explanation this way

    def visit_seealso(self, node):
        self.body.append("\nSee also: \n")

    def depart_seealso(self, node):
        pass

    def visit_todo_node(self, node):
        self.body.append("To do: ")

    def depart_todo_node(self, node):
        pass

    def visit_download_reference(self, node):
        self.body.append("Download reference: ")

    def depart_download_reference(self, node):
        pass

    def visit_graphviz(self, node):
        self.body.append("Graphviz: ")

    def depart_graphviz(self, node):
        pass

    def visit_container(self, node):
        self.body.append("[stem]\n")
        self.body.append("++++")

    def depart_container(self, node):
        self.body.append("++++")


if __name__ == "__main__":
    """To test the writer"""
    from docutils.core import publish_string

    filename = sys.argv[-1]
    print("Converting: " + filename)
    f_in = open(filename, "rb")
    rtf = publish_string(f_in.read(), writer=AsciiDocWriter())
    f_in.close()

    filename = filename + ".adoc"

    f_out = open(filename, "wb")
    f_out.write(rtf)
    print("Converted file: " + filename)
    f_out.close()
