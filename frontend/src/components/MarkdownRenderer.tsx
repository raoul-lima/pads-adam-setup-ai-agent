'use client';

import React from 'react';
import Markdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { a11yDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  isAI: boolean;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="markdown-container">
      <Markdown
        components={{
          h1: ({...props}) => <h1 className="text-2xl font-bold my-4" {...props} />,
          h2: ({...props}) => <h2 className="text-xl font-bold my-3" {...props} />,
          h3: ({...props}) => <h3 className="text-lg font-bold my-2" {...props} />,
          ul: ({...props}) => <ul className="list-disc list-inside my-4" {...props} />,
          ol: ({...props}) => <ol className="list-decimal list-inside my-4" {...props} />,
          li: ({...props}) => <li className="mb-2" {...props} />,
          p: ({ node, ...props }) => {
            // Check if paragraph contains a single code block, if so, render it without a p tag
            if (node && node.children && node.children.length === 1 && node.children[0].type === 'element' && node.children[0].tagName === 'pre') {
              return <>{props.children}</>;
            }
            return <p className="mb-3 last:mb-0 leading-relaxed" {...props} />;
          },
          code({ className, children, ...props }) {
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { ref, ...rest } = props;
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children).replace(/\n$/, '');

            return match ? (
              <div className="my-4 relative">
                <button
                  onClick={() => handleCopy(codeString)}
                  className="absolute top-2 right-2 p-1.5 bg-gray-600 rounded-md text-white hover:bg-gray-700 transition-colors"
                >
                  {copied ? <Check size={16} /> : <Copy size={16} />}
                </button>
                <SyntaxHighlighter
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  style={a11yDark as any}
                  language={match[1]}
                  PreTag="pre"
                  className="p-4 rounded-lg overflow-x-auto text-sm"
                  {...rest}
                >
                  {codeString}
                </SyntaxHighlighter>
              </div>
            ) : (
              <code className="bg-gray-200 text-gray-800 px-1 rounded" {...rest}>
                {children}
              </code>
            );
          },
        }}
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
      >
        {content}
      </Markdown>
    </div>
  );
};

export default MarkdownRenderer; 