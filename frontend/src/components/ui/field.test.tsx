import { render, screen } from "@testing-library/react";

import { Field } from "./field";
import { Input } from "./input";

describe("Field", () => {
  it("links the label, description and errors to the control", () => {
    render(
      <Field label="Email" htmlFor="email" description="We never share it." error={["Enter a valid email address."]}>
        <Input />
      </Field>,
    );
    const input = screen.getByLabelText("Email");
    expect(input).toHaveAttribute("id", "email");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input).toHaveAccessibleDescription("We never share it. Enter a valid email address.");
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email address.");
  });

  it("is quiet when valid", () => {
    render(
      <Field label="Name" htmlFor="name" optional>
        <Input />
      </Field>,
    );
    expect(screen.getByRole("textbox")).not.toHaveAttribute("aria-invalid");
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByText("(optional)")).toBeInTheDocument();
  });
});
