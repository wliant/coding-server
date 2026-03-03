// Ensure Node.js built-in Web API globals are available in jsdom test environment
import { ReadableStream } from "stream/web";
import { TextDecoder, TextEncoder } from "util";
import "@testing-library/jest-dom";

Object.assign(global, { TextDecoder, TextEncoder, ReadableStream });
