"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Building2, Check, ChevronDown, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { MAJOR_COMPANIES } from "./constants/companies";

interface CompanyComboboxProps {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

interface ComboboxOption {
  type: "company" | "custom";
  label: string;
  value: string;
}

export function CompanyCombobox({
  id,
  value,
  onChange,
  disabled = false,
  placeholder = "Select or enter company...",
}: CompanyComboboxProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const trimmedQuery = searchQuery.trim();

  const filteredCompanies = useMemo(() => {
    if (!trimmedQuery) return MAJOR_COMPANIES;
    const lower = trimmedQuery.toLowerCase();
    return MAJOR_COMPANIES.filter((company) =>
      company.toLowerCase().includes(lower),
    );
  }, [trimmedQuery]);

  const isExactMatch = useMemo(() => {
    if (!trimmedQuery) return false;
    const lower = trimmedQuery.toLowerCase();
    return MAJOR_COMPANIES.some((c) => c.toLowerCase() === lower);
  }, [trimmedQuery]);

  const showCustomOption = trimmedQuery.length > 0 && !isExactMatch;

  const options = useMemo<ComboboxOption[]>(() => {
    const list: ComboboxOption[] = [];

    if (showCustomOption && filteredCompanies.length === 0) {
      list.push({
        type: "custom",
        label: `Use "${trimmedQuery}"`,
        value: trimmedQuery,
      });
    } else if (showCustomOption) {
      filteredCompanies.forEach((company) => {
        list.push({ type: "company", label: company, value: company });
      });
      list.push({
        type: "custom",
        label: `Use "${trimmedQuery}"`,
        value: trimmedQuery,
      });
    } else {
      filteredCompanies.forEach((company) => {
        list.push({ type: "company", label: company, value: company });
      });
    }

    return list;
  }, [filteredCompanies, showCustomOption, trimmedQuery]);

  useEffect(() => {
    if (isOpen) {
      requestAnimationFrame(() => {
        searchInputRef.current?.focus();
      });
      setHighlightedIndex(0);
    } else {
      setSearchQuery("");
      setHighlightedIndex(-1);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && highlightedIndex >= 0 && listRef.current) {
      const activeEl = listRef.current.children[
        highlightedIndex
      ] as HTMLElement | undefined;
      if (activeEl) {
        activeEl.scrollIntoView({ block: "nearest" });
      }
    }
  }, [highlightedIndex, isOpen]);

  function handleSelect(val: string) {
    onChange(val);
    setIsOpen(false);
    triggerRef.current?.focus();
  }

  function handleSearchKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        options.length > 0 ? (prev + 1) % options.length : -1,
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        options.length > 0 ? (prev - 1 + options.length) % options.length : -1,
      );
    } else if (e.key === "Enter") {
      e.preventDefault();
      const targetOption = options[highlightedIndex];
      if (targetOption) {
        handleSelect(targetOption.value);
      } else if (trimmedQuery) {
        handleSelect(trimmedQuery);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
    }
  }

  function handleTriggerKeyDown(e: React.KeyboardEvent<HTMLButtonElement>) {
    if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setIsOpen(true);
    }
  }

  return (
    <div ref={containerRef} className="relative w-full">
      <button
        ref={triggerRef}
        type="button"
        id={id}
        disabled={disabled}
        onClick={() => setIsOpen((prev) => !prev)}
        onKeyDown={handleTriggerKeyDown}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        className={cn(
          "input-3d flex h-11 w-full items-center justify-between rounded-xl px-3.5 py-2 text-sm text-left transition-colors focus-visible:outline-none focus:ring-2 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          !value && "text-muted-foreground/80",
        )}
      >
        <div className="flex items-center gap-2 truncate pr-2">
          <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
          <span
            className={cn(
              "truncate",
              value
                ? "font-medium text-foreground"
                : "text-muted-foreground/80",
            )}
          >
            {value || placeholder}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0 text-muted-foreground">
          {value && !disabled && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
                onChange("");
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.stopPropagation();
                  e.preventDefault();
                  onChange("");
                }
              }}
              className="rounded p-0.5 hover:text-foreground transition-colors cursor-pointer"
              aria-label="Clear company selection"
            >
              <X className="h-3.5 w-3.5" />
            </span>
          )}
          <ChevronDown
            className={cn(
              "h-4 w-4 transition-transform duration-200",
              isOpen && "rotate-180",
            )}
          />
        </div>
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-1.5 w-full rounded-xl border border-border bg-popover/95 p-1.5 shadow-xl backdrop-blur-md">
          <div className="relative mb-1.5 px-1 pt-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setHighlightedIndex(0);
              }}
              onKeyDown={handleSearchKeyDown}
              placeholder="Search MNC or type company name..."
              className="input-3d h-9 w-full rounded-lg pl-9 pr-8 text-sm focus-visible:outline-none"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  searchInputRef.current?.focus();
                }}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-0.5"
                aria-label="Clear search input"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <ul
            ref={listRef}
            role="listbox"
            className="max-h-60 overflow-y-auto overscroll-contain rounded-lg p-1 space-y-0.5 text-sm"
          >
            {options.map((option, index) => {
              const isSelected =
                value.toLowerCase() === option.value.toLowerCase();
              const isHighlighted = highlightedIndex === index;

              return (
                <li
                  key={`${option.type}-${option.value}`}
                  role="option"
                  aria-selected={isSelected}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  onClick={() => handleSelect(option.value)}
                  className={cn(
                    "flex items-center justify-between px-2.5 py-2 rounded-lg cursor-pointer transition-colors select-none",
                    isHighlighted
                      ? "bg-accent text-accent-foreground font-medium"
                      : "text-foreground hover:bg-accent/50",
                    option.type === "custom" &&
                      "border border-dashed border-primary/40 bg-primary/5 text-primary",
                  )}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className="truncate">{option.label}</span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0 ml-2">
                    {option.type === "custom" && (
                      <span className="text-[11px] px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium">
                        Custom
                      </span>
                    )}
                    {isSelected && <Check className="h-4 w-4 text-primary" />}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
