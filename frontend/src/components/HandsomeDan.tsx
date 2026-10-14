// Original cartoon of Handsome Dan, the Yale bulldog, drawn as inline SVG.
// `face` renders just the head (for the logo and chat button).

interface Props {
  size?: number
  face?: boolean
  className?: string
  title?: string
}

export default function HandsomeDan({ size = 200, face = false, className, title = 'Handsome Dan, the Yale bulldog' }: Props) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox={face ? '22 26 156 140' : '0 0 200 220'}
      role={title ? 'img' : undefined}
      aria-label={title || undefined}
      aria-hidden={title ? undefined : true}
    >
      {title && <title>{title}</title>}

      {!face && (
        <g>
          {/* Yale-blue sweater with a white Y */}
          <path d="M28 220 C30 170 60 148 100 148 C140 148 170 170 172 220 Z" fill="#00356b" />
          <path d="M62 156 C78 168 122 168 138 156 L134 150 C118 160 82 160 66 150 Z" fill="#0f4c8a" />
          <path d="M84 176 L100 196 L116 176 M100 196 L100 214" stroke="#fff" strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </g>
      )}

      {/* ears */}
      <path d="M40 58 C26 40 34 28 52 34 C62 38 66 50 62 60 Z" fill="#b98a5e" stroke="#3b2a1e" strokeWidth="3" strokeLinejoin="round" />
      <path d="M160 58 C174 40 166 28 148 34 C138 38 134 50 138 60 Z" fill="#b98a5e" stroke="#3b2a1e" strokeWidth="3" strokeLinejoin="round" />

      {/* head */}
      <path
        d="M100 38 C150 38 172 66 170 100 C168 132 146 156 100 158 C54 156 32 132 30 100 C28 66 50 38 100 38 Z"
        fill="#f5e6d3"
        stroke="#3b2a1e"
        strokeWidth="3"
      />
      {/* brindle eye patch */}
      <path d="M118 60 C140 56 156 70 152 92 C144 100 126 96 118 84 Z" fill="#d4a57a" />

      {/* brow wrinkles */}
      <path d="M80 56 C92 50 108 50 120 56" stroke="#3b2a1e" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      <path d="M86 64 C95 60 105 60 114 64" stroke="#3b2a1e" strokeWidth="2.5" fill="none" strokeLinecap="round" />

      {/* eyes */}
      <ellipse cx="72" cy="84" rx="11" ry="12" fill="#fff" stroke="#3b2a1e" strokeWidth="2.5" />
      <ellipse cx="128" cy="84" rx="11" ry="12" fill="#fff" stroke="#3b2a1e" strokeWidth="2.5" />
      <circle cx="74" cy="86" r="6" fill="#2b1d14" />
      <circle cx="126" cy="86" r="6" fill="#2b1d14" />
      <circle cx="76" cy="83" r="2" fill="#fff" />
      <circle cx="128" cy="83" r="2" fill="#fff" />

      {/* cheeks */}
      <ellipse cx="54" cy="116" rx="10" ry="6" fill="#ff8fb8" opacity="0.6" />
      <ellipse cx="146" cy="116" rx="10" ry="6" fill="#ff8fb8" opacity="0.6" />

      {/* muzzle and jowls */}
      <path
        d="M62 118 C62 100 80 96 100 96 C120 96 138 100 138 118 C138 138 122 148 100 148 C78 148 62 138 62 118 Z"
        fill="#fffaf2"
        stroke="#3b2a1e"
        strokeWidth="2.5"
      />
      {/* nose */}
      <path d="M86 104 C86 98 114 98 114 104 C114 112 106 116 100 116 C94 116 86 112 86 104 Z" fill="#2b1d14" />
      <ellipse cx="95" cy="103" rx="3" ry="1.6" fill="#6b5a4e" />
      {/* mouth with classic bulldog underbite */}
      <path d="M100 116 L100 124" stroke="#3b2a1e" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M76 126 C86 140 114 140 124 126" fill="#c2415f" stroke="#3b2a1e" strokeWidth="2.5" strokeLinejoin="round" />
      <path d="M84 129 L87 121 L91 131 Z" fill="#fff" stroke="#3b2a1e" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M116 129 L113 121 L109 131 Z" fill="#fff" stroke="#3b2a1e" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}
