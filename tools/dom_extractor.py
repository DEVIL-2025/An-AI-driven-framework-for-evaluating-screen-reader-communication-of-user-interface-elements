"""
DOM / Structural Snapshot Extractor Module (Website-Independent & Generic)
Extracts a compact, bounded, accessibility-relevant structural representation
of any webpage from an active Selenium WebDriver instance.

CRITICAL GENERICITY & ARCHITECTURAL PRINCIPLES:
1. Pure Evidence Collection: Does NOT analyze violations, judge compliance, or assign scores.
   Gemini remains the sole accessibility reasoning authority.
2. Completely Website-Independent: Zero hardcoded website names, domains, URLs, portal labels,
   custom theme classnames (e.g. databox, sublogo), or invented heading strings.
3. DOM-Driven Structural Grouping: Discovers meaningful context groups from:
   - Semantic HTML elements (<header>, <nav>, <main>, <section>, <article>, <footer>, <fieldset>, <form>, <dialog>)
   - Standard ARIA structural roles (banner, navigation, main, contentinfo, search, form, region, group, feed, tabpanel)
   - Heading-anchored containers (any container whose initial content begins with a heading)
   - Repeated interactive structures (grids, lists, or card rows containing >= 3 interactive children)
4. Contextual Heading Precision: Associates headings with interactive elements ONLY when supported
   by genuine local container or local document flow relationships; strictly returns null otherwise.
5. Clean Surrounding Context: Captures substantive local descriptive text; returns null rather than
   empty brackets or bare punctuation.
6. Non-Intrusive: Does NOT move focus, press keys, or manipulate browser state.
7. Robust: Handles duplicate IDs, minimal HTML, and script execution errors gracefully.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("DOMExtractor")

DOM_EXTRACTION_SCRIPT = """
var maxTextLen = arguments[0] || 150;
var maxHeadings = arguments[1] || 100;
var maxLandmarks = arguments[2] || 50;
var maxSections = arguments[3] || 50;
var maxInteractive = arguments[4] || 150;
var maxImages = arguments[5] || 50;

function cleanText(str, maxLen) {
    if (!str) return "";
    var s = ("" + str).replace(/\\s+/g, " ").trim();
    if (maxLen && s.length > maxLen) {
        return s.substring(0, maxLen) + "...";
    }
    return s;
}

function getElementCleanText(el, maxLen) {
    if (!el) return "";
    try {
        var clone = el.cloneNode(true);
        var noise = clone.querySelectorAll("script, style, noscript, svg, template");
        for (var n = 0; n < noise.length; n++) {
            if (noise[n].parentNode) {
                noise[n].parentNode.removeChild(noise[n]);
            }
        }
        var txt = (clone.textContent || clone.innerText || "").replace(/\\s+/g, " ").trim();
        if (maxLen && txt.length > maxLen) {
            return txt.substring(0, maxLen) + "...";
        }
        return txt;
    } catch (e) {
        var fallback = (el.textContent || el.innerText || "").replace(/\\s+/g, " ").trim();
        return maxLen && fallback.length > maxLen ? fallback.substring(0, maxLen) + "..." : fallback;
    }
}

function getCssPath(el) {
    if (!el || el.nodeType !== 1) return "";
    var path = [];
    var curr = el;
    var depth = 0;
    while (curr && curr.nodeType === 1 && curr !== document.documentElement && depth < 6) {
        var selector = curr.tagName.toLowerCase();
        if (curr.id) {
            var matchingIdCount = 0;
            try {
                matchingIdCount = document.querySelectorAll("[id='" + CSS.escape(curr.id) + "']").length;
            } catch (e) {
                matchingIdCount = document.querySelectorAll("#" + curr.id).length;
            }
            if (matchingIdCount === 1) {
                selector += "#" + curr.id;
                path.unshift(selector);
                break;
            } else {
                selector += "#" + curr.id;
                var sib = curr;
                var nthId = 1;
                while ((sib = sib.previousElementSibling)) {
                    if (sib.tagName.toLowerCase() === curr.tagName.toLowerCase()) nthId++;
                }
                if (nthId > 1) selector += ":nth-of-type(" + nthId + ")";
            }
        } else {
            var sibling = curr;
            var nth = 1;
            while ((sibling = sibling.previousElementSibling)) {
                if (sibling.tagName.toLowerCase() === curr.tagName.toLowerCase()) nth++;
            }
            if (nth > 1) selector += ":nth-of-type(" + nth + ")";
        }
        path.unshift(selector);
        curr = curr.parentElement;
        depth++;
    }
    return path.join(" > ");
}

var LANDMARK_TAG_MAP = {
    "MAIN": "main",
    "NAV": "navigation",
    "ASIDE": "complementary",
    "FOOTER": "contentinfo",
    "HEADER": "banner",
    "FORM": "form",
    "SEARCH": "search"
};

var VALID_LANDMARK_ROLES = [
    "banner", "main", "navigation", "complementary", "contentinfo", "search", "form", "region"
];

function getEnclosingLandmark(el) {
    var curr = el.parentElement;
    while (curr && curr !== document.body && curr !== document.documentElement) {
        var role = (curr.getAttribute("role") || "").toLowerCase().trim();
        if (VALID_LANDMARK_ROLES.indexOf(role) !== -1) {
            return role;
        }
        var tag = curr.tagName.toUpperCase();
        if (LANDMARK_TAG_MAP[tag]) {
            if (tag === "HEADER" || tag === "FOOTER") {
                var parentSection = curr.closest ? curr.closest("article, section, aside, nav") : null;
                if (!parentSection) {
                    return LANDMARK_TAG_MAP[tag];
                }
            } else {
                return LANDMARK_TAG_MAP[tag];
            }
        }
        if (tag === "SECTION" && (curr.getAttribute("aria-label") || curr.getAttribute("aria-labelledby"))) {
            return "region";
        }
        curr = curr.parentElement;
    }
    return null;
}

// Universal DOM-level calculation: total interactive controls on page
var totalPageInteractive = document.querySelectorAll("a, button, input:not([type='hidden']), select, textarea").length;

function isBroadPageLayoutContainer(el) {
    if (!el || el === document.body || el === document.documentElement) return true;
    if (totalPageInteractive > 5) {
        var count = el.querySelectorAll("a, button, input:not([type='hidden']), select, textarea").length;
        if (count >= Math.floor(totalPageInteractive * 0.7)) {
            return true;
        }
    }
    return false;
}

function getGenericBlockType(el) {
    var tag = el.tagName.toLowerCase();
    var role = (el.getAttribute("role") || "").toLowerCase();
    var cls = (el.className && typeof el.className === "string" ? el.className.toLowerCase() : "");

    if (tag === "header" || role === "banner" || cls.indexOf("navbar") !== -1 || cls.indexOf("nav-bar") !== -1 || cls.indexOf("header") !== -1) return "header";
    if (tag === "nav" || role === "navigation") return "navigation";
    if (tag === "footer" || role === "contentinfo" || cls.indexOf("footer") !== -1) return "footer";
    if (tag === "form" || tag === "fieldset" || role === "form") return "form-group";
    if (tag === "dialog" || role === "dialog" || role === "alertdialog") return "dialog";
    if (cls.indexOf("panel") !== -1) return "panel";
    if (cls.indexOf("card") !== -1) return "card-group";
    if (tag === "section" || tag === "article" || role === "region" || role === "group" || role === "tabpanel") return "content-group";
    return "content-group";
}

function getEnclosingMeaningfulContainer(el) {
    var curr = el.parentElement;
    var depth = 0;
    while (curr && depth < 5 && !isBroadPageLayoutContainer(curr)) {
        var tag = curr.tagName.toLowerCase();
        var role = (curr.getAttribute("role") || "").toLowerCase();
        var cls = (curr.className && typeof curr.className === "string" ? curr.className.toLowerCase() : "");

        var isSemantic = (
            tag === "section" || tag === "article" || tag === "fieldset" || tag === "form" ||
            tag === "dialog" || tag === "header" || tag === "nav" || tag === "footer" || tag === "aside" ||
            role === "region" || role === "group" || role === "tabpanel" || role === "dialog" ||
            cls.indexOf("navbar") !== -1 || cls.indexOf("panel") !== -1 || cls.indexOf("card") !== -1
        );

        // Heading-anchored container check (semantic heading or heading/title class)
        var firstHeading = curr.querySelector("h1, h2, h3, h4, h5, h6, [role='heading'], legend, summary, [class*='heading'], [class*='title']");
        var hasHeadingAnchor = firstHeading && (curr.firstElementChild === firstHeading || (curr.firstElementChild && curr.firstElementChild.contains(firstHeading)));

        // Repeated interactive children check (grid, card list, action group)
        var hasRepeatedInteractive = false;
        if (curr.children && curr.children.length >= 2) {
            var activeKids = 0;
            for (var c = 0; c < curr.children.length; c++) {
                if (curr.children[c].querySelector("a, button, input:not([type='hidden']), select, textarea") ||
                    curr.children[c].tagName === "A" || curr.children[c].tagName === "BUTTON") {
                    activeKids++;
                }
            }
            if (activeKids >= 2) hasRepeatedInteractive = true;
        }

        if (isSemantic || hasHeadingAnchor || hasRepeatedInteractive) {
            var hText = firstHeading ? getElementCleanText(firstHeading, 80) : null;
            var blockType = hasRepeatedInteractive ? (cls.indexOf("card") !== -1 ? "card-group" : "repeated-group") : (hasHeadingAnchor ? (cls.indexOf("panel") !== -1 ? "panel" : "heading-group") : getGenericBlockType(curr));
            return {
                tag: tag,
                id: curr.id || "",
                class: cleanText(curr.className, 50),
                block_type: blockType,
                heading: hText
            };
        }

        curr = curr.parentElement;
        depth++;
    }
    return null;
}

function getNearestHeading(el) {
    if (!el) return null;

    // 1. Check local container (within 4 parent levels, stopping before whole-page wrappers)
    var curr = el.parentElement;
    var depth = 0;
    while (curr && depth < 4 && !isBroadPageLayoutContainer(curr)) {
        var h = curr.querySelector("h1, h2, h3, h4, h5, h6, [role='heading'], legend");
        if (h && h !== el && !h.contains(el)) {
            // Must strictly precede el in document flow
            if ((h.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0) {
                var hTag = h.tagName.toLowerCase();
                var hLevel = parseInt(h.getAttribute("aria-level") || (hTag.length === 2 && !isNaN(hTag[1]) ? hTag[1] : null), 10);
                return {
                    tag: hTag,
                    level: isNaN(hLevel) ? null : hLevel,
                    text: getElementCleanText(h, 80),
                    id: h.id || ""
                };
            }
        }
        curr = curr.parentElement;
        depth++;
    }

    // 2. Preceding heading in local document flow
    try {
        var allH = document.querySelectorAll("h1, h2, h3, h4, h5, h6, [role='heading']");
        var lastPreceding = null;
        for (var i = 0; i < allH.length; i++) {
            var cand = allH[i];
            if ((cand.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0) {
                lastPreceding = cand;
            } else {
                break;
            }
        }
        if (lastPreceding) {
            // Proximity check: Must share a common local ancestor that is not body
            var common = el.parentElement;
            var depthC = 0;
            while (common && depthC < 5 && common !== document.body) {
                if (common.contains(lastPreceding)) {
                    var lpTag = lastPreceding.tagName.toLowerCase();
                    var lpLevel = parseInt(lastPreceding.getAttribute("aria-level") || (lpTag.length === 2 && !isNaN(lpTag[1]) ? lpTag[1] : 2), 10);
                    return {
                        tag: lpTag,
                        level: isNaN(lpLevel) ? 2 : lpLevel,
                        text: getElementCleanText(lastPreceding, 80),
                        id: lastPreceding.id || ""
                    };
                }
                common = common.parentElement;
                depthC++;
            }
        }
    } catch (e) {}

    return null;
}

function getSurroundingText(el, maxLen) {
    if (!el || !el.parentElement) return null;
    var parent = el.parentElement;

    var full = getElementCleanText(parent, maxLen * 2);
    var selfText = getElementCleanText(el, maxLen);

    var remainder = "";
    if (full && selfText && full.indexOf(selfText) !== -1) {
        remainder = full.replace(selfText, " ").replace(/\\s+/g, " ").trim();
    } else if (full && full !== selfText) {
        remainder = full;
    }

    // Substantive text verification (>= 2 alphanumeric characters)
    if (remainder && remainder.replace(/[^a-zA-Z0-9]/g, "").length >= 2) {
        return cleanText(remainder, maxLen);
    }

    // Check immediate siblings
    var prev = el.previousElementSibling;
    if (prev) {
        var prevText = getElementCleanText(prev, maxLen);
        if (prevText && prevText.replace(/[^a-zA-Z0-9]/g, "").length >= 2) {
            return cleanText(prevText, maxLen);
        }
    }
    var next = el.nextElementSibling;
    if (next) {
        var nextText = getElementCleanText(next, maxLen);
        if (nextText && nextText.replace(/[^a-zA-Z0-9]/g, "").length >= 2) {
            return cleanText(nextText, maxLen);
        }
    }

    // Check parent's siblings if parent was just a single-child wrapper
    if (parent.children.length === 1 && parent.parentElement && !isBroadPageLayoutContainer(parent.parentElement)) {
        var pPrev = parent.previousElementSibling;
        if (pPrev) {
            var pPrevText = getElementCleanText(pPrev, maxLen);
            if (pPrevText && pPrevText.replace(/[^a-zA-Z0-9]/g, "").length >= 2) {
                return cleanText(pPrevText, maxLen);
            }
        }
        var pNext = parent.nextElementSibling;
        if (pNext) {
            var pNextText = getElementCleanText(pNext, maxLen);
            if (pNextText && pNextText.replace(/[^a-zA-Z0-9]/g, "").length >= 2) {
                return cleanText(pNextText, maxLen);
            }
        }
    }

    // Check grandparent paragraph, list item, table cell, or compact container
    if (parent.parentElement && !isBroadPageLayoutContainer(parent.parentElement)) {
        var gp = parent.parentElement;
        var gpTag = gp.tagName.toUpperCase();
        if (gpTag === "LI" || gpTag === "P" || gpTag === "DD" || gpTag === "TD" || gpTag === "TH" || (parent.children.length === 1 && gp.children.length <= 4)) {
            var gpFull = getElementCleanText(gp, maxLen * 2);
            var gpRemainder = (gpFull && selfText && gpFull.indexOf(selfText) !== -1) ? gpFull.replace(selfText, " ").replace(/\\s+/g, " ").trim() : gpFull;
            if (gpRemainder && gpRemainder.replace(/[^a-zA-Z0-9]/g, "").length >= 2) {
                return cleanText(gpRemainder, maxLen);
            }
        }
    }

    return null;
}

// 1. Page Metadata
var pageMetadata = {
    "title": cleanText(document.title, 120),
    "lang": (document.documentElement.getAttribute("lang") || document.documentElement.getAttribute("xml:lang") || "").trim(),
    "url": cleanText(window.location.href, 200)
};

// 2. Headings
var headingNodes = document.querySelectorAll("h1, h2, h3, h4, h5, h6, [role='heading']");
var headings = [];
for (var i = 0; i < headingNodes.length && headings.length < maxHeadings; i++) {
    var hEl = headingNodes[i];
    var tag = hEl.tagName.toLowerCase();
    var levelAttr = hEl.getAttribute("aria-level");
    var level = parseInt(levelAttr || (tag.length === 2 && !isNaN(tag[1]) ? tag[1] : 2), 10);
    if (isNaN(level)) level = 2;

    headings.push({
        "level": level,
        "tag": tag,
        "text": getElementCleanText(hEl, maxTextLen),
        "id": hEl.id || "",
        "landmark": getEnclosingLandmark(hEl),
        "aria_hidden": hEl.getAttribute("aria-hidden") === "true",
        "css_path": getCssPath(hEl)
    });
}

// 3. Landmarks
var landmarkElements = document.querySelectorAll(
    "header, nav, main, aside, footer, form, search, section[aria-label], section[aria-labelledby], " +
    "[role='banner'], [role='main'], [role='navigation'], [role='complementary'], " +
    "[role='contentinfo'], [role='search'], [role='form'], [role='region']"
);
var landmarks = [];
var seenLandmarkNodes = [];

for (var j = 0; j < landmarkElements.length && landmarks.length < maxLandmarks; j++) {
    var lEl = landmarkElements[j];
    if (seenLandmarkNodes.indexOf(lEl) !== -1) continue;
    seenLandmarkNodes.push(lEl);

    var lTag = lEl.tagName.toUpperCase();
    var lRole = (lEl.getAttribute("role") || "").toLowerCase().trim();
    var finalRole = lRole || LANDMARK_TAG_MAP[lTag] || (lTag === "SECTION" ? "region" : "region");

    if (!lRole && (lTag === "HEADER" || lTag === "FOOTER")) {
        var sectionAncestor = lEl.closest ? lEl.closest("article, section, aside, nav") : null;
        if (sectionAncestor) continue;
    }

    var label = lEl.getAttribute("aria-label") || "";
    var labelledBy = lEl.getAttribute("aria-labelledby");
    if (!label && labelledBy) {
        var labelTarget = document.getElementById(labelledBy);
        if (labelTarget) {
            label = getElementCleanText(labelTarget, 80);
        }
    }

    landmarks.push({
        "role": finalRole,
        "tag": lTag.toLowerCase(),
        "id": lEl.id || "",
        "label": cleanText(label, 80),
        "aria_hidden": lEl.getAttribute("aria-hidden") === "true",
        "css_path": getCssPath(lEl)
    });
}

// 4. Sections & Meaningful Context Blocks (100% Generic & DOM-Driven)
var sections = [];
var seenSectionNodes = [];

function normalizeText(str) {
    if (!str) return "";
    return String(str).toLowerCase().replace(/\\s+/g, " ").trim();
}

function getNonInteractiveText(el) {
    if (!el) return "";
    try {
        var clone = el.cloneNode(true);
        var noise = clone.querySelectorAll("script, style, noscript, svg, template");
        for (var n = 0; n < noise.length; n++) {
            if (noise[n].parentNode) noise[n].parentNode.removeChild(noise[n]);
        }
        var itNodes = clone.querySelectorAll("a, button, input, select, textarea, [role='button'], [role='link']");
        for (var i = 0; i < itNodes.length; i++) {
            if (itNodes[i].parentNode) itNodes[i].parentNode.removeChild(itNodes[i]);
        }
        return (clone.textContent || clone.innerText || "").replace(/\\s+/g, " ").trim();
    } catch (e) {
        return "";
    }
}

function isRedundantNestedBlock(el, blockType, headingText) {
    for (var i = 0; i < sections.length; i++) {
        var pNode = seenSectionNodes[i];
        if (pNode && pNode !== el && pNode.contains(el)) {
            var pSec = sections[i];
            var tag = el.tagName.toLowerCase();
            var role = el.getAttribute("role");
            var isDistinctSemantic = (tag === "nav" || tag === "form" || tag === "footer" || tag === "header" || tag === "dialog" || tag === "article" || tag === "section" || tag === "aside" || tag === "main" || role);
            if (!isDistinctSemantic) {
                // 1. Heading check: distinct heading contributes independent context
                var elHeading = headingText ? headingText.trim() : "";
                var parentHeading = pSec.heading ? pSec.heading.trim() : "";
                var hasDistinctHeading = elHeading.length > 0 && normalizeText(elHeading) !== normalizeText(parentHeading);
                if (hasDistinctHeading) {
                    continue;
                }

                // 2. Interactive elements check:
                var childIt = el.querySelectorAll("a, button, input:not([type='hidden']), select, textarea, [role='button'], [role='link']");
                var childItCount = childIt.length;
                var parentItCount = pSec.interactive_elements_count;
                var sameOrZeroIt = (childItCount === 0 || childItCount === parentItCount);

                if (!sameOrZeroIt) {
                    // Distinct subset of interactive elements -> NOT redundant
                    continue;
                }

                // 3. Candidate & Parent non-interactive text extraction
                var cText = (getElementCleanText(el, maxTextLen) || "").trim();
                var pText = (pSec.contextual_text || "").trim();
                var childNonIt = getNonInteractiveText(el);
                var parentNonIt = getNonInteractiveText(pNode);

                var childNonItNorm = normalizeText(childNonIt);
                var parentNonItNorm = normalizeText(parentNonIt);
                var childSubstantive = childNonIt.replace(/[^a-zA-Z0-9]/g, "");
                var hasMeaningfulChildText = childSubstantive.length >= 2;

                if (childItCount > 0) {
                    // When candidate has interactive elements:
                    // Redundant if it has NO meaningful contextual text outside the controls,
                    // OR if its non-interactive text is effectively identical to the parent's (duplicate evidence).
                    var isEffectivelyIdentical = (childNonItNorm.length > 0 && childNonItNorm === parentNonItNorm);
                    if (!hasMeaningfulChildText || isEffectivelyIdentical) {
                        return true;
                    }
                } else {
                    // When candidate has 0 interactive elements:
                    // Redundant if empty, identical to parent text, duplicate of parent heading,
                    // or effectively identical to parent non-interactive text.
                    var isEffectivelyIdenticalText = (normalizeText(cText) === normalizeText(pText));
                    var isParentHeadingDuplicate = (parentHeading && normalizeText(cText) === normalizeText(parentHeading));
                    var isNonItIdentical = (childNonItNorm.length > 0 && childNonItNorm === parentNonItNorm);
                    if (cText === "" || isEffectivelyIdenticalText || isParentHeadingDuplicate || isNonItIdentical) {
                        return true;
                    }
                }
            }
        }
    }
    return false;
}

function addContextBlock(el, blockType, headingText, headingLevel) {
    if (!el || seenSectionNodes.indexOf(el) !== -1 || isBroadPageLayoutContainer(el) || sections.length >= maxSections) {
        return;
    }
    if (isRedundantNestedBlock(el, blockType, headingText)) {
        return;
    }
    seenSectionNodes.push(el);
    var blockIndex = sections.length + 1;
    var blockId = "context-" + (blockIndex < 10 ? "0" : "") + blockIndex;
    sections.push({
        "block_id": blockId,
        "tag": el.tagName.toLowerCase(),
        "id": el.id || "",
        "class": cleanText(el.className, 50),
        "block_type": blockType,
        "heading": headingText || null,
        "heading_level": (headingLevel !== null && !isNaN(headingLevel)) ? headingLevel : null,
        "landmark": getEnclosingLandmark(el),
        "contextual_text": getElementCleanText(el, maxTextLen),
        "interactive_elements_count": el.querySelectorAll("a, button, input:not([type='hidden']), select, textarea").length,
        "css_path": getCssPath(el)
    });
}

// A. Semantic elements & ARIA landmarks + Generic UI components (navbars, panels, cards)
var semanticContainers = document.querySelectorAll(
    "section, article, fieldset, form, header, nav, footer, aside, dialog, details, " +
    "[role='region'], [role='group'], [role='banner'], [role='navigation'], [role='contentinfo'], " +
    "[role='search'], [role='form'], [role='feed'], [role='tabpanel'], [role='dialog'], " +
    "div[class*='navbar'], div[class*='nav-bar'], div[class*='panel'], div[class*='card']"
);

for (var k = 0; k < semanticContainers.length && sections.length < maxSections; k++) {
    var sEl = semanticContainers[k];
    if (seenSectionNodes.indexOf(sEl) !== -1) continue;

    var sHeading = sEl.querySelector("h1, h2, h3, h4, h5, h6, [role='heading'], legend, summary, [class*='heading'], [class*='title']");
    var sHeadingText = sHeading ? getElementCleanText(sHeading, 80) : null;
    var sHeadingLevel = null;
    if (sHeading) {
        var sHTag = sHeading.tagName.toLowerCase();
        var sHAttr = sHeading.getAttribute("aria-level");
        sHeadingLevel = parseInt(sHAttr || (sHTag.length === 2 && !isNaN(sHTag[1]) ? sHTag[1] : null), 10);
        if (isNaN(sHeadingLevel)) sHeadingLevel = null;
    }

    addContextBlock(sEl, getGenericBlockType(sEl), sHeadingText, sHeadingLevel);
}

// B. Heading-anchored containers (containers starting with a heading)
for (var hIdx = 0; hIdx < headingNodes.length && sections.length < maxSections; hIdx++) {
    var hNode = headingNodes[hIdx];
    var hText = getElementCleanText(hNode, 80);
    if (!hText) continue;
    var hParent = hNode.parentElement;
    if (hParent && !isBroadPageLayoutContainer(hParent) && seenSectionNodes.indexOf(hParent) === -1) {
        var hPHeadTag = hNode.tagName.toLowerCase();
        var hPHeadAttr = hNode.getAttribute("aria-level");
        var hPHeadLevel = parseInt(hPHeadAttr || (hPHeadTag.length === 2 && !isNaN(hPHeadTag[1]) ? hPHeadTag[1] : null), 10);

        addContextBlock(hParent, "heading-group", hText, isNaN(hPHeadLevel) ? null : hPHeadLevel);
    }
}

// C. Repeated interactive structures (grids, card lists, action groups)
var candidateContainers = document.querySelectorAll("div, ul, ol");
for (var cIdx = 0; cIdx < candidateContainers.length && sections.length < maxSections; cIdx++) {
    var cEl = candidateContainers[cIdx];
    if (seenSectionNodes.indexOf(cEl) !== -1 || isBroadPageLayoutContainer(cEl)) continue;
    var kids = cEl.children;
    if (kids && kids.length >= 2) {
        var activeChildCount = 0;
        for (var kc = 0; kc < kids.length; kc++) {
            if (kids[kc].querySelector("a, button, input:not([type='hidden']), select, textarea") ||
                kids[kc].tagName === "A" || kids[kc].tagName === "BUTTON") {
                activeChildCount++;
            }
        }
        if (activeChildCount >= 2) {
            var cCls = (cEl.className && typeof cEl.className === "string" ? cEl.className.toLowerCase() : "");
            var rBlockType = (cCls.indexOf("card") !== -1 ? "card-group" : "repeated-group");
            addContextBlock(cEl, rBlockType, null, null);
        }
    }
}

// 5. Interactive Elements
var interactiveSelector = "a[href], button, input:not([type='hidden']), select, textarea, [role='button'], [role='link'], [role='checkbox'], [role='radio'], [role='switch'], [role='tab'], [role='menuitem'], [role='combobox'], [tabindex]:not([tabindex='-1'])";
var interactiveNodes = document.querySelectorAll(interactiveSelector);
var interactiveElements = [];

for (var m = 0; m < interactiveNodes.length && interactiveElements.length < maxInteractive; m++) {
    var itEl = interactiveNodes[m];
    var itTag = itEl.tagName.toLowerCase();
    var itType = itEl.getAttribute("type") || (itTag === "button" ? "button" : null);
    var itRole = itEl.getAttribute("role");
    var tabIndex = itEl.getAttribute("tabindex");

    var visibleText = getElementCleanText(itEl, maxTextLen);
    if (!visibleText) {
        visibleText = cleanText(itEl.value || itEl.getAttribute("placeholder") || itEl.getAttribute("title") || "", maxTextLen);
    }
    var ariaLabel = itEl.getAttribute("aria-label");
    var ariaLabelledBy = itEl.getAttribute("aria-labelledby");
    var resolvedLabelledBy = "";
    if (ariaLabelledBy) {
        var lbEl = document.getElementById(ariaLabelledBy);
        if (lbEl) resolvedLabelledBy = getElementCleanText(lbEl, 80);
    }

    var parentBlockId = null;
    var parentBlockRef = null;
    var currCont = itEl.parentElement;
    while (currCont && currCont !== document.body && currCont !== document.documentElement) {
        var sIdx = seenSectionNodes.indexOf(currCont);
        if (sIdx !== -1) {
            parentBlockId = sections[sIdx].block_id;
            parentBlockRef = sections[sIdx];
            break;
        }
        currCont = currCont.parentElement;
    }

    var enclosingLm = getEnclosingLandmark(itEl);
    var nearH = getNearestHeading(itEl);
    var surroundingTxt = getSurroundingText(itEl, 100);

    interactiveElements.push({
        "tag": itTag,
        "id": itEl.id || "",
        "name": itEl.getAttribute("name") || "",
        "type": itType,
        "text": visibleText,
        "href": itEl.getAttribute("href") ? cleanText(itEl.getAttribute("href"), 120) : null,
        "role": itRole,
        "tabindex": tabIndex !== null ? parseInt(tabIndex, 10) : null,
        "aria_label": ariaLabel,
        "aria_labelledby": ariaLabelledBy,
        "aria_labelledby_text": resolvedLabelledBy || null,
        "aria_describedby": itEl.getAttribute("aria-describedby"),
        "aria_expanded": itEl.getAttribute("aria-expanded"),
        "aria_hidden": itEl.getAttribute("aria-hidden") === "true",
        "parent_section_id": parentBlockId,
        "parent_section": parentBlockRef ? (parentBlockRef.heading || parentBlockRef.block_type) : null,
        "parent_landmark": enclosingLm,
        "nearest_heading": nearH ? nearH.text : null,
        "nearest_heading_level": nearH ? nearH.level : null,
        "surrounding_text": surroundingTxt,
        "css_path": getCssPath(itEl)
    });
}

// 6. Forms
var formNodes = document.querySelectorAll("form");
var forms = [];
for (var f = 0; f < formNodes.length && forms.length < 20; f++) {
    var fEl = formNodes[f];
    var fLabel = fEl.getAttribute("aria-label") || "";
    if (!fLabel && fEl.getAttribute("aria-labelledby")) {
        var fLb = document.getElementById(fEl.getAttribute("aria-labelledby"));
        if (fLb) fLabel = getElementCleanText(fLb, 80);
    }
    var fieldsCount = fEl.querySelectorAll("input:not([type='hidden']), select, textarea, button").length;
    forms.push({
        "id": fEl.id || "",
        "name": fEl.getAttribute("name") || "",
        "action": cleanText(fEl.getAttribute("action") || "", 100),
        "method": (fEl.getAttribute("method") || "get").toLowerCase(),
        "label": fLabel || null,
        "field_count": fieldsCount,
        "css_path": getCssPath(fEl)
    });
}

// 7. Images (100% Generic & DOM-Driven)
var imgNodes = document.querySelectorAll("img, svg[role='img'], [role='img']");
var images = [];
for (var g = 0; g < imgNodes.length && images.length < maxImages; g++) {
    var imEl = imgNodes[g];
    var altVal = imEl.getAttribute("alt");
    var isDecorative = altVal === "" || imEl.getAttribute("aria-hidden") === "true" || imEl.getAttribute("role") === "presentation" || imEl.getAttribute("role") === "none";
    var srcVal = imEl.getAttribute("src") || imEl.currentSrc || null;
    if (srcVal && srcVal.length > 150) srcVal = srcVal.substring(0, 150) + "...";

    // Generic parent context determination
    var parentContext = "content";
    var brandContainer = imEl.closest("[class*='brand'], [class*='logo'], [id*='logo'], [id*='brand']");
    if (brandContainer) {
        parentContext = "brand";
    } else if (imEl.closest("button")) {
        parentContext = "button";
    } else if (imEl.closest("a")) {
        parentContext = "link";
    } else if (imEl.closest("header, [role='banner'], [class*='navbar'], [class*='header']")) {
        parentContext = "header";
    } else if (imEl.closest("nav, [role='navigation']")) {
        parentContext = "navigation";
    } else if (imEl.closest("footer, [role='contentinfo'], [class*='footer']")) {
        parentContext = "footer";
    }

    // Generic nearby text extraction (enclosing link text, figcaption, label, or direct container text)
    var nearbyText = null;
    var enclosingInteractive = imEl.closest("a, button");
    if (enclosingInteractive) {
        var linkTxt = getElementCleanText(enclosingInteractive, 100);
        if (linkTxt && linkTxt.length > 1) nearbyText = linkTxt;
    }
    if (!nearbyText) {
        var figcap = imEl.closest("figure") ? imEl.closest("figure").querySelector("figcaption") : null;
        if (figcap) {
            nearbyText = getElementCleanText(figcap, 100);
        } else {
            var startFrom = enclosingInteractive ? enclosingInteractive.parentElement : imEl.parentElement;
            while (startFrom && !nearbyText && !isBroadPageLayoutContainer(startFrom)) {
                var nearbyContainer = startFrom.closest("header, [role='banner'], [class*='navbar'], [class*='header'], nav, [role='navigation'], [class*='panel'], [class*='card'], figure") || startFrom;
                if (nearbyContainer && !isBroadPageLayoutContainer(nearbyContainer)) {
                    var pTxt = getElementCleanText(nearbyContainer, 100);
                    if (pTxt && pTxt.length > 1) {
                        nearbyText = pTxt;
                        break;
                    }
                }
                startFrom = (nearbyContainer && nearbyContainer !== startFrom) ? nearbyContainer.parentElement : startFrom.parentElement;
            }
        }
    }

    var imgParentBlockId = null;
    var imgCurrCont = imEl.parentElement;
    while (imgCurrCont && imgCurrCont !== document.body && imgCurrCont !== document.documentElement) {
        var imIdx = seenSectionNodes.indexOf(imgCurrCont);
        if (imIdx !== -1) {
            imgParentBlockId = sections[imIdx].block_id;
            break;
        }
        imgCurrCont = imgCurrCont.parentElement;
    }

    images.push({
        "tag": imEl.tagName.toLowerCase(),
        "id": imEl.id || "",
        "src": srcVal,
        "alt": altVal,
        "title": imEl.getAttribute("title"),
        "aria_label": imEl.getAttribute("aria-label"),
        "role": imEl.getAttribute("role"),
        "width": imEl.getAttribute("width") || (imEl.naturalWidth ? String(imEl.naturalWidth) : null),
        "height": imEl.getAttribute("height") || (imEl.naturalHeight ? String(imEl.naturalHeight) : null),
        "is_decorative": isDecorative,
        "aria_hidden": imEl.getAttribute("aria-hidden") === "true",
        "parent_landmark": getEnclosingLandmark(imEl),
        "parent_section_id": imgParentBlockId,
        "parent_context": parentContext,
        "nearby_text": nearbyText,
        "css_path": getCssPath(imEl)
    });
}

return {
    "status": "SUCCESS",
    "page_metadata": pageMetadata,
    "headings": headings,
    "landmarks": landmarks,
    "sections": sections,
    "interactive_elements": interactiveElements,
    "forms": forms,
    "images": images,
    "counts": {
        "total_headings": headings.length,
        "total_landmarks": landmarks.length,
        "total_sections": sections.length,
        "total_interactive": interactiveElements.length,
        "total_forms": forms.length,
        "total_images": images.length
    }
};
"""


def extract_dom_snapshot(
    driver: Any,
    max_text_len: int = 150,
    max_headings: int = 100,
    max_landmarks: int = 50,
    max_sections: int = 50,
    max_interactive: int = 150,
    max_images: int = 50,
) -> Dict[str, Any]:
    """
    Extracts a bounded, compact structural DOM snapshot from an active Selenium WebDriver.

    Args:
        driver: Active Selenium WebDriver instance (or compatible test mock).
        max_text_len: Maximum length for string text snippets (default: 150 chars).
        max_headings: Maximum number of headings captured (default: 100).
        max_landmarks: Maximum number of landmarks captured (default: 50).
        max_sections: Maximum number of semantic sections/context blocks captured (default: 50).
        max_interactive: Maximum number of interactive elements captured (default: 150).
        max_images: Maximum number of images captured (default: 50).

    Returns:
        Structured dictionary containing page metadata, headings, landmarks, sections,
        interactive elements, forms, and images.
        Never raises exceptions; returns a structured fallback dict on failure.
    """
    if driver is None:
        logger.warning("WebDriver is None; cannot extract DOM snapshot.")
        return _fallback_snapshot(error="WebDriver instance was None")

    try:
        raw_result = driver.execute_script(
            DOM_EXTRACTION_SCRIPT,
            max_text_len,
            max_headings,
            max_landmarks,
            max_sections,
            max_interactive,
            max_images,
        )

        if not isinstance(raw_result, dict):
            logger.warning(f"Unexpected non-dict DOM snapshot returned: {type(raw_result)}")
            return _fallback_snapshot(error="JavaScript did not return a valid dictionary")

        return sanitize_dom_snapshot(raw_result)

    except Exception as e:
        logger.error(f"DOM structural snapshot extraction failed: {e}", exc_info=True)
        return _fallback_snapshot(error=str(e))


def sanitize_dom_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures consistent schema and safely bounded types in the snapshot dict."""
    status = snapshot.get("status", "SUCCESS")
    meta = snapshot.get("page_metadata") or {}
    headings = snapshot.get("headings") or []
    landmarks = snapshot.get("landmarks") or []
    sections = snapshot.get("sections") or []
    interactive = snapshot.get("interactive_elements") or []
    forms = snapshot.get("forms") or []
    images = snapshot.get("images") or []
    counts = snapshot.get("counts") or {
        "total_headings": len(headings),
        "total_landmarks": len(landmarks),
        "total_sections": len(sections),
        "total_interactive": len(interactive),
        "total_forms": len(forms),
        "total_images": len(images),
    }

    return {
        "status": status,
        "page_metadata": {
            "title": str(meta.get("title", "")),
            "lang": str(meta.get("lang", "")),
            "url": str(meta.get("url", "")),
        },
        "headings": headings if isinstance(headings, list) else [],
        "landmarks": landmarks if isinstance(landmarks, list) else [],
        "sections": sections if isinstance(sections, list) else [],
        "interactive_elements": interactive if isinstance(interactive, list) else [],
        "forms": forms if isinstance(forms, list) else [],
        "images": images if isinstance(images, list) else [],
        "counts": counts,
    }


def _fallback_snapshot(error: str) -> Dict[str, Any]:
    """Produces a clean, valid fallback snapshot when extraction encounters an issue."""
    return {
        "status": "EXTRACTION_FAILED",
        "error": error,
        "page_metadata": {
            "title": "",
            "lang": "",
            "url": "",
        },
        "headings": [],
        "landmarks": [],
        "sections": [],
        "interactive_elements": [],
        "forms": [],
        "images": [],
        "counts": {
            "total_headings": 0,
            "total_landmarks": 0,
            "total_sections": 0,
            "total_interactive": 0,
            "total_forms": 0,
            "total_images": 0,
        },
    }
