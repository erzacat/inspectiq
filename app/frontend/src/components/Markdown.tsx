/**
 * Minimal markdown renderer — handles what our agents actually emit:
 * headings (# ## ###), bold (**), italic (*), inline code (`), code blocks (```),
 * bullet lists (-), numbered lists, horizontal rules (---), GFM tables.
 *
 * No external deps (npm registry is blocked on this machine).
 */
import { ReactNode } from 'react'

// Parse inline formatting: **bold**, *italic*, `code`, and links [text](url)
function parseInline(text: string): ReactNode[] {
  // Split on formatting tokens while keeping them. Precedence: code > bold > italic.
  const tokens: ReactNode[] = []
  let i = 0
  let key = 0

  while (i < text.length) {
    // Inline code `...`
    if (text[i] === '`') {
      const end = text.indexOf('`', i + 1)
      if (end > i) {
        tokens.push(<code key={key++}>{text.slice(i + 1, end)}</code>)
        i = end + 1
        continue
      }
    }
    // Bold **...**
    if (text[i] === '*' && text[i + 1] === '*') {
      const end = text.indexOf('**', i + 2)
      if (end > i) {
        tokens.push(<strong key={key++}>{parseInline(text.slice(i + 2, end))}</strong>)
        i = end + 2
        continue
      }
    }
    // Italic *...* (single star, must not be bold)
    if (text[i] === '*' && text[i + 1] !== '*') {
      const end = text.indexOf('*', i + 1)
      if (end > i && text[end + 1] !== '*') {
        tokens.push(<em key={key++}>{text.slice(i + 1, end)}</em>)
        i = end + 1
        continue
      }
    }
    // Link [text](url)
    if (text[i] === '[') {
      const close = text.indexOf(']', i)
      if (close > i && text[close + 1] === '(') {
        const urlEnd = text.indexOf(')', close + 2)
        if (urlEnd > close) {
          tokens.push(
            <a
              key={key++}
              href={text.slice(close + 2, urlEnd)}
              target="_blank"
              rel="noreferrer"
            >
              {text.slice(i + 1, close)}
            </a>
          )
          i = urlEnd + 1
          continue
        }
      }
    }
    // Plain character — coalesce run of non-special chars
    let j = i
    while (j < text.length && !'`*['.includes(text[j])) j++
    if (j > i) {
      tokens.push(text.slice(i, j))
      i = j
    } else {
      tokens.push(text[i])
      i++
    }
  }
  return tokens
}

// Detect GFM table: header row + separator row (| --- | --- |) + body rows
function isTableSeparator(line: string): boolean {
  return /^\s*\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$/.test(line)
}

function splitTableRow(line: string): string[] {
  let s = line.trim()
  if (s.startsWith('|')) s = s.slice(1)
  if (s.endsWith('|')) s = s.slice(0, -1)
  return s.split('|').map(c => c.trim())
}

export default function Markdown({ children }: { children: string }) {
  const blocks: ReactNode[] = []
  const lines = children.split('\n')
  let i = 0
  let key = 0

  while (i < lines.length) {
    const line = lines[i]

    // Code block ```
    if (line.startsWith('```')) {
      const lang = line.slice(3).trim()
      const end = lines.findIndex((l, k) => k > i && l.startsWith('```'))
      const codeEnd = end === -1 ? lines.length : end
      const code = lines.slice(i + 1, codeEnd).join('\n')
      blocks.push(
        <pre key={key++}>
          <code className={lang ? `language-${lang}` : undefined}>{code}</code>
        </pre>
      )
      i = codeEnd + 1
      continue
    }

    // Horizontal rule
    if (/^\s*---+\s*$/.test(line)) {
      blocks.push(<hr key={key++} />)
      i++
      continue
    }

    // Heading
    const hMatch = line.match(/^(#{1,4})\s+(.+)$/)
    if (hMatch) {
      const level = hMatch[1].length
      const content = parseInline(hMatch[2])
      if (level === 1) blocks.push(<h1 key={key++}>{content}</h1>)
      else if (level === 2) blocks.push(<h2 key={key++}>{content}</h2>)
      else if (level === 3) blocks.push(<h3 key={key++}>{content}</h3>)
      else blocks.push(<h3 key={key++}>{content}</h3>)
      i++
      continue
    }

    // Table — look ahead for separator
    if (line.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const headerCells = splitTableRow(line)
      let j = i + 2
      const rows: string[][] = []
      while (j < lines.length && lines[j].trim().startsWith('|')) {
        rows.push(splitTableRow(lines[j]))
        j++
      }
      blocks.push(
        <table key={key++}>
          <thead>
            <tr>
              {headerCells.map((cell, ci) => (
                <th key={ci}>{parseInline(cell)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri}>
                {row.map((cell, ci) => (
                  <td key={ci}>{parseInline(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )
      i = j
      continue
    }

    // Bulleted list
    if (/^\s*[-*]\s+/.test(line)) {
      const items: ReactNode[] = []
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(<li key={key++}>{parseInline(lines[i].replace(/^\s*[-*]\s+/, ''))}</li>)
        i++
      }
      blocks.push(<ul key={key++}>{items}</ul>)
      continue
    }

    // Numbered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: ReactNode[] = []
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(<li key={key++}>{parseInline(lines[i].replace(/^\s*\d+\.\s+/, ''))}</li>)
        i++
      }
      blocks.push(<ol key={key++}>{items}</ol>)
      continue
    }

    // Empty line — block separator
    if (line.trim() === '') { i++; continue }

    // Paragraph — collect consecutive non-empty non-special lines
    const paraLines: string[] = [line]
    i++
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('#') &&
      !lines[i].startsWith('```') &&
      !/^\s*---+\s*$/.test(lines[i]) &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i]) &&
      !(lines[i].includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
    ) {
      paraLines.push(lines[i])
      i++
    }
    blocks.push(<p key={key++}>{parseInline(paraLines.join(' '))}</p>)
  }

  return <>{blocks}</>
}
